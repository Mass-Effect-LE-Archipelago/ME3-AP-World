// LE3 research bridge. Development delivery requires an explicit build option.
#include "Delivery.hpp"
#include "CareerTrace.hpp"
#include "Common/Base.hpp"
#include "Common/DefaultLogger.hpp"
#include "Common/Objects.hpp"
#include <SPI.h>
#include <atomic>
#include <charconv>
#include <chrono>
#include <future>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#ifndef LE3AP_DELIVERY_DEV
#define LE3AP_DELIVERY_DEV 0
#endif
#ifndef LE3AP_CAREER_TRACE
#define LE3AP_CAREER_TRACE 0
#endif

namespace {
constexpr wchar_t PipeName[] = L"\\\\.\\pipe\\LE3APBridge";
constexpr DWORD BufferSize = 65536;
constexpr int MaxPlotIndex = 65535;
std::atomic<bool> Stopping{false};
std::atomic<bool> HasPending{false};
std::mutex PendingMutex;
struct Pending {
    std::string operation;
    std::vector<int> indices;
    Delivery::Request delivery;
    std::promise<std::string> reply;
    std::atomic<bool> cancelled{false};
};
std::shared_ptr<Pending> Next;
using ProcessEvent = void(UObject*, UFunction*, void*, void*);
ProcessEvent* Original = nullptr;
thread_local bool InRead = false;
// Resolve a hot-path function at most once per second until it exists, so an
// early or missing name never turns every ProcessEvent into an object scan.
// Atomic publication: ProcessEvent can run on several engine threads.
UFunction* Resolve(std::atomic<UFunction*>& cached, std::atomic<ULONGLONG>& retry, wchar_t const* name) {
    if (auto* found = cached.load()) return found;
    ULONGLONG const now = GetTickCount64();
    ULONGLONG due = retry.load();
    if (now < due || !retry.compare_exchange_strong(due, now + 1000)) return nullptr;
    auto* found = UObject::FindObject<UFunction>(name);
    if (found) cached.store(found);
    return found;
}
// Last HUD world, refreshed every frame on the game thread; used by the landing gate.
std::atomic<ABioWorldInfo*> FrameWorld{nullptr};

bool Live(UObject* object) {
    return object && !Common::IsDefaultObject(object) && !Common::IsDestroyed(object);
}

#if LE3AP_CAREER_TRACE
#include "CareerObserver.hpp"
#endif

std::string Utf8(FString const& text) {
    if (text.Empty()) return "";
    int size = WideCharToMultiByte(CP_UTF8, 0, text.Chars(), static_cast<int>(text.Length()), nullptr, 0, nullptr, nullptr);
    std::string result(static_cast<size_t>(size), '\0');
    WideCharToMultiByte(CP_UTF8, 0, text.Chars(), static_cast<int>(text.Length()), result.data(), size, nullptr, nullptr);
    return result;
}

struct DeliveryHost {
    ABioWorldInfo* world;
    UBioGlobalVariableTable* variables;
    UFunction* getInt;
    ASFXInventoryManager* inventory = nullptr;
    int read(int index) {
        struct Parameters { int index, value = 0; } parameters{index};
        Original(variables, getInt, &parameters, nullptr);
        return parameters.value;
    }
    void write(int index, int value) {
        if (!LE3AP_DELIVERY_DEV) throw std::runtime_error("delivery_disabled");
        if (index < Delivery::Base || index >= Delivery::Base + Delivery::Slots) throw std::runtime_error("write_range");
        static auto* setter = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.SetInt");
        if (!setter || !(setter->FunctionFlags & 0x400)) throw std::runtime_error("no_setter");
        struct Parameters { int index, value; unsigned long skipProcessing = 1; } parameters{index, value};
        static_assert(sizeof(Parameters) == 12);
        Original(variables, setter, &parameters, nullptr);
        if (read(index) != value) throw std::runtime_error("write_readback");
    }
    int readBool(int index) {
        static auto* getter = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.GetBool");
        if (!getter || !(getter->FunctionFlags & 0x400)) throw std::runtime_error("no_bool_getter");
        struct Parameters { int index, value = 0; } parameters{index};
        Original(variables, getter, &parameters, nullptr);
        return parameters.value != 0;
    }
    // Only the salvage flags (bought/available/tier) and mission access bools are writable.
    void writeBool(int index, bool value) {
        if (!LE3AP_DELIVERY_DEV) throw std::runtime_error("delivery_disabled");
        bool const salvage = index >= Delivery::BoughtBool && index < Delivery::SalvageBoolEnd;
        bool const key = index >= Delivery::KeyBool && index < Delivery::KeyBool + Delivery::MaxKeys;
        if (!salvage && !key) throw std::runtime_error("bool_range");
        static auto* setter = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.SetBool");
        if (!setter || !(setter->FunctionFlags & 0x400)) throw std::runtime_error("no_bool_setter");
        struct Parameters { int index; unsigned long value, evaluateAchievement = 0, skipProcessing = 1; } parameters{index, value ? 1ul : 0ul};
        static_assert(sizeof(Parameters) == 16);
        Original(variables, setter, &parameters, nullptr);
        if (readBool(index) != static_cast<int>(value)) throw std::runtime_error("bool_readback");
    }
    bool completed() {
        static auto* getter = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.GetBool");
        if (!getter) throw std::runtime_error("no_goal_reader");
        struct Parameters { int index = 22426, value = 0; } parameters;
        Original(variables, getter, &parameters, nullptr);
        return parameters.value != 0;
    }
    ASFXInventoryManager* playerInventory() {
        if (inventory) return inventory;
        auto* controller = world->LocalPlayerController;
        if (!Live(controller) || !Live(controller->Pawn) || !Live(controller->Pawn->InvManager))
            throw std::runtime_error("noplayer");
        inventory = controller->Pawn->InvManager->Cast<ASFXInventoryManager>();
        if (!Live(inventory) || inventory->Instigator != controller->Pawn || !world->m_oTreasure)
            throw std::runtime_error("noinventory");
        return inventory;
    }
    Delivery::Wallet wallet() { auto* inv = playerInventory(); return {inv->Credits, inv->MaxCredits}; }
    void adjustCredits(int amount) {
        if (!LE3AP_DELIVERY_DEV) throw std::runtime_error("delivery_disabled");
        auto* inv = playerInventory();
        static auto* adjust = UObject::FindObject<UFunction>(L"Function SFXGame.SFXInventoryManager.AdjustResource");
        if (!adjust) throw std::runtime_error("no_credit_function");
        struct Parameters { unsigned char type = 0; int amount; unsigned long notification = 0, ignoreBudget = 1; } parameters{};
        static_assert(sizeof(Parameters) == 16);
        parameters.amount = amount;
        Original(inv, adjust, &parameters, nullptr);
    }
    void restoreCredits(int value) {
        if (!LE3AP_DELIVERY_DEV) throw std::runtime_error("delivery_disabled");
        playerInventory()->Credits = value;
    }
    // Weapon ownership is the SFXEngine player variable "SFXGameContent.<class>" (1 = owned), as a pickup records it.
    USFXEngine* engine() {
        auto* objects = UObject::GObjObjects;
        if (!objects || !objects->GetData()) throw std::runtime_error("noengine");
        for (UINT i = 0; i < objects->Count(); i++) {
            auto* object = objects->GetData()[i];
            if (Live(object)) if (auto* found = object->Cast<USFXEngine>()) return found;
        }
        throw std::runtime_error("noengine");
    }
    static SFXName weaponName(int id) {
        auto const& cls = Weapons::Classes.at(static_cast<std::size_t>(id));
        std::wstring name = L"SFXGameContent.";
        name.append(cls.begin(), cls.end());
        return SFXName(name.c_str(), 0, false);
    }
    int weaponOwned(int id) {
        static auto* getter = UObject::FindObject<UFunction>(L"Function SFXGame.SFXEngine.GetPlayerVariable");
        if (!getter || !(getter->FunctionFlags & 0x400)) throw std::runtime_error("no_playervar_getter");
        struct Parameters { SFXName name; int value = 0; } parameters{weaponName(id)};
        static_assert(sizeof(SFXName) == 8);
        Original(engine(), getter, &parameters, nullptr);
        return parameters.value;
    }
    void setWeaponOwned(int id, int value) {
        if (!LE3AP_DELIVERY_DEV) throw std::runtime_error("delivery_disabled");
        static auto* setter = UObject::FindObject<UFunction>(L"Function SFXGame.SFXEngine.SetPlayerVariable");
        if (!setter || !(setter->FunctionFlags & 0x400)) throw std::runtime_error("no_playervar_setter");
        struct Parameters { SFXName name; int value; } parameters{weaponName(id), value};
        static_assert(sizeof(Parameters) == 12);
        Original(engine(), setter, &parameters, nullptr);
    }
};

#if LE3AP_DELIVERY_DEV
// Cerberus HQ landing gate. Galaxy map calls the BioPlanet.CanBeInteractedWith
// event natively (no script caller); vanilla's own condition still applies.
bool CerberusLandingBlocked(UObject* context) {
    auto* planet = context ? context->Cast<UBioPlanet>() : nullptr;
    // Cronos Station (Cerberus HQ) is BioP_Cat004; Earth is BioP_End001. Gate both.
    if (!planet || planet->MapName.Empty()) return false;
    auto const* map = planet->MapName.Chars();
    if (_wcsicmp(map, L"BioP_Cat004") != 0 && _wcsicmp(map, L"BioP_End001") != 0) return false;
    static UFunction* getTable = UObject::FindObject<UFunction>(L"Function SFXGame.BioWorldInfo.GetGlobalVariables");
    static UFunction* getInt = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.GetInt");
    // Without a readable plot table the save's AP state is unknown: fail closed.
    auto* world = FrameWorld.load();
    if (!Live(world) || !getTable || !getInt || !(getTable->FunctionFlags & 0x400) || !(getInt->FunctionFlags & 0x400)) return true;
    struct TableResult { UBioGlobalVariableTable* value = nullptr; } table;
    Original(world, getTable, &table, nullptr);
    if (!table.value || Common::IsDestroyed(table.value)) return true;
    DeliveryHost host{world, table.value, getInt};
    return Delivery::gateBlocks(host);
}
#endif

std::string Read(Pending const& request, ABioWorldInfo* world) {
    if (!Live(world)) return "ERR noworld";
    if (request.operation == "MAP") {
        UObject* outer = world;
        for (int depth = 0; outer->Outer && depth < 64; depth++) outer = outer->Outer;
        return "OK " + Utf8(outer->GetName());
    }
    if (request.operation == "GAW") {
        auto* controller = world->LocalPlayerController;
        if (!Live(controller) || !Live(controller->Player)) return "ERR noplayer";
        auto* player = controller->Player->Cast<USFXLocalPlayer>();
        if (!player || !Live(player->GAWHandler)) return "ERR nogaw";
        auto const& assets = player->GAWHandler->UnlockedGAWAssets;
        if (assets.Count() > 1024 || (assets.Count() && !assets.GetData())) return "ERR invalidgaw";
        std::string result = "OK " + std::to_string(assets.Count());
        for (UINT i = 0; i < assets.Count(); i++) {
            auto const& asset = assets.GetData()[i];
            result += " " + std::to_string(asset.Id) + ":" + std::to_string(asset.Strength);
        }
        return result;
    }
    if (request.operation == "USES") {
        USFXEngine* engine = nullptr;
        auto* objects = UObject::GObjObjects;
        if (!objects || !objects->GetData()) return "ERR noengine";
        for (UINT i = 0; i < objects->Count(); i++) {
            auto* object = objects->GetData()[i];
            if (Live(object) && (engine = object->Cast<USFXEngine>())) break;
        }
        if (!engine) return "ERR noengine";
        auto const& used = engine->UseModuleList;
        if (used.Count() > 65535 || (used.Count() && !used.GetData())) return "ERR invaliduses";
        UINT const start = static_cast<UINT>(request.indices[0]);
        UINT const end = (std::min)(used.Count(), start + static_cast<UINT>(request.indices[1]));
        std::string result = "OK " + std::to_string(used.Count());
        for (UINT i = start; i < end; i++) {
            auto const& guid = used.GetData()[i];
            result += " " + std::to_string(guid.A) + ":" + std::to_string(guid.B)
                + ":" + std::to_string(guid.C) + ":" + std::to_string(guid.D);
        }
        return result;
    }
    // Generated SDK wrappers use `FunctionFlags |= ~0x400`, corrupting every
    // non-native flag. Dispatch the read-only native functions directly and
    // preserve their flags exactly. All calls remain on the HUD/game thread.
    static UFunction* getTable = UObject::FindObject<UFunction>(L"Function SFXGame.BioWorldInfo.GetGlobalVariables");
    static UFunction* getBool = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.GetBool");
    static UFunction* getInt = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.GetInt");
    if (!getTable || !getBool || !getInt) return "ERR noplotfunctions";
    if (!(getTable->FunctionFlags & 0x400) || !(getBool->FunctionFlags & 0x400) || !(getInt->FunctionFlags & 0x400))
        return "ERR nonnativeplotfunctions";
    struct TableResult { UBioGlobalVariableTable* value = nullptr; } table;
    Original(world, getTable, &table, nullptr);
    auto* variables = table.value;
    if (!variables) return "ERR noplots_null";
    if (Common::IsDestroyed(variables)) return "ERR noplots_destroyed";
    if (!variables->Cast<UBioGlobalVariableTable>()) return "ERR noplots_type";
    if (request.operation.starts_with("DEV_")) {
        DeliveryHost host{world, variables, getInt};
        try { return Delivery::execute(request.delivery, host); }
        catch (std::exception const& error) { return "ERR " + std::string(error.what()); }
    }
    // GetGlobalVariables is the authoritative accessor. Its returned table may
    // be a class default singleton; actor-instance filtering is inappropriate
    // for this service object. Report that distinction for runtime validation.
    if (request.operation == "PLOTINFO") {
        return "OK name=" + Utf8(variables->GetName())
            + " default=" + std::to_string(Common::IsDefaultObject(variables))
            + " flags=" + std::to_string(variables->ObjectFlags)
            + " bool_words=" + std::to_string(variables->BoolVariables.Count())
            + " get_table_flags=" + std::to_string(getTable->FunctionFlags)
            + " get_bool_flags=" + std::to_string(getBool->FunctionFlags)
            + " get_int_flags=" + std::to_string(getInt->FunctionFlags);
    }
    std::string result = "OK";
    bool const booleans = request.operation == "GETB" || request.operation == "GETBS";
    for (int index : request.indices) {
        struct PlotResult { int index; int value = 0; } plot{index};
        Original(variables, booleans ? getBool : getInt, &plot, nullptr);
        result += " " + std::to_string(booleans ? static_cast<int>(plot.value != 0) : plot.value);
    }
    return result;
}

void Hook(UObject* context, UFunction* function, void* parameters, void* result) {
#if LE3AP_CAREER_TRACE
    CareerObserver::Observation observe(context, function, CareerTrace::Route::Event);
#endif
    // Only the HUD frame callback drains requests. Other engine threads and SDK
    // re-entrancy cannot run the game-facing readers.
    static std::atomic<UFunction*> frameCache{nullptr};
    static std::atomic<ULONGLONG> frameRetry{0};
    UFunction* const frame = function ? Resolve(frameCache, frameRetry, L"Function SFXGame.BioHUD.PostRender") : nullptr;
    if (frame && function == frame && Live(context)) {
        auto* actor = context->Cast<AActor>();
        FrameWorld.store(actor && Live(actor->WorldInfo) ? actor->WorldInfo->Cast<ABioWorldInfo>() : nullptr);
    }
    if (HasPending.load() && !InRead && function) {
        if (frame && function == frame && Live(context)) {
            auto* actor = context->Cast<AActor>();
            if (actor) {
                std::shared_ptr<Pending> request;
                {
                    std::lock_guard lock(PendingMutex);
                    request = std::move(Next);
                    HasPending.store(false);
                }
                if (request && !request->cancelled.load()) {
                    InRead = true;
                    try { request->reply.set_value(Read(*request, Live(actor->WorldInfo) ? actor->WorldInfo->Cast<ABioWorldInfo>() : nullptr)); }
                    catch (...) { request->reply.set_value("ERR exception"); }
                    InRead = false;
                }
            }
        }
    }
    Original(context, function, parameters, result);
#if LE3AP_DELIVERY_DEV
    static std::atomic<UFunction*> landingCache{nullptr};
    static std::atomic<ULONGLONG> landingRetry{0};
    UFunction* const landing = function ? Resolve(landingCache, landingRetry, L"Function SFXGame.BioPlanet.CanBeInteractedWith") : nullptr;
    if (landing && function == landing && parameters && function->ReturnValueOffset >= 0) {
        auto* allowed = reinterpret_cast<unsigned long*>(static_cast<char*>(parameters) + function->ReturnValueOffset);
        if (*allowed) {
            try { if (CerberusLandingBlocked(context)) *allowed = 0; }
            catch (...) { *allowed = 0; }
        }
    }
#endif
}

std::string Parse(std::string const& message, Pending& request) {
    if (message.empty() || message.size() > 4096) return "ERR badrequest";
    for (unsigned char c : message) if (c < 32 || c > 126) return "ERR badrequest";
    std::istringstream stream(message);
    stream >> request.operation;
    if (request.operation == "CAREER_TRACE") {
#if LE3AP_CAREER_TRACE
        std::uint64_t after = 0;
        unsigned limit = 0;
        if (!CareerTrace::parse(message, after, limit)) return "ERR badrequest";
        return CareerObserver::Records.page(after, limit, CareerObserver::TargetMask.load());
#else
        return "ERR career_trace_disabled";
#endif
    }
    if (request.operation.starts_with("DEV_")) {
        auto error = Delivery::parse(message, request.delivery);
        if (!error.empty()) return error;
        if (Delivery::writes(request.delivery) && !LE3AP_DELIVERY_DEV) return "ERR delivery_disabled";
        return "";
    }
    std::string token;
    while (stream >> token) {
        int value = 0;
        auto [end, error] = std::from_chars(token.data(), token.data() + token.size(), value);
        if (error != std::errc{} || end != token.data() + token.size() || value < 0 || value > MaxPlotIndex)
            return "ERR badrequest";
        if (request.indices.size() == 64) return "ERR badrequest";
        request.indices.push_back(value);
    }
    auto const count = request.indices.size();
    auto const& op = request.operation;
    if (op == "PING" && !count) return "OK pong";
    if (op == "VER" && !count) return LE3AP_CAREER_TRACE ? "OK 0.3.0-career-trace"
        : LE3AP_DELIVERY_DEV ? "OK 0.2.4-delivery-dev" : "OK 0.2.0-research";
    if (op == "CAPS" && !count && LE3AP_CAREER_TRACE)
        return "OK readonly CAREER_TRACE GETB GETBS GETI GETIS MAP GAW USES PLOTINFO DEV_SESSION DEV_WALLET";
    if (op == "CAPS" && !count) return LE3AP_DELIVERY_DEV
        ? "OK delivery_dev GETB GETBS GETI GETIS MAP GAW USES PLOTINFO DEV_SESSION DEV_WALLET DEV_GATE DEV_BIND DEV_TXN LANDING_GATE WEAPONS SALVAGE KEYS"
        : "OK readonly GETB GETBS GETI GETIS MAP GAW USES PLOTINFO DEV_SESSION DEV_WALLET";
    if (op == "HELLO" && count == 1) return request.indices[0] == 1 ? "OK 1 LE3 readonly" : "ERR protocol";
    if ((op == "MAP" || op == "GAW" || op == "PLOTINFO") && !count) return "";
    if (op == "USES" && count == 2 && request.indices[1] > 0 && request.indices[1] <= 128) return "";
    if ((op == "GETB" || op == "GETI") && count == 1) return "";
    if ((op == "GETBS" || op == "GETIS") && count > 0) return "";
    return "ERR badrequest";
}

void Send(HANDLE pipe, std::string const& text) {
    DWORD written = 0;
    WriteFile(pipe, text.data(), static_cast<DWORD>(text.size()), &written, nullptr);
}

void Serve() {
    while (!Stopping.load()) {
        HANDLE pipe = CreateNamedPipeW(PipeName, PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
            PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
            1, BufferSize, BufferSize, 0, nullptr);
        if (pipe == INVALID_HANDLE_VALUE) return;
        if (ConnectNamedPipe(pipe, nullptr) || GetLastError() == ERROR_PIPE_CONNECTED) {
            std::vector<char> buffer(BufferSize);
            DWORD received = 0;
            while (!Stopping.load() && ReadFile(pipe, buffer.data(), BufferSize, &received, nullptr)) {
                auto request = std::make_shared<Pending>();
                std::string immediate = Parse(std::string(buffer.data(), received), *request);
                if (!immediate.empty()) { Send(pipe, immediate); continue; }
                auto future = request->reply.get_future();
                {
                    std::lock_guard lock(PendingMutex);
                    if (Next) Next->cancelled.store(true);
                    Next = request;
                    HasPending.store(true);
                }
                if (future.wait_for(std::chrono::seconds(5)) == std::future_status::ready) Send(pipe, future.get());
                else { request->cancelled.store(true); Send(pipe, "ERR timeout"); }
            }
        }
        DisconnectNamedPipe(pipe);
        CloseHandle(pipe);
    }
}
}

SPI_PLUGINSIDE_SUPPORT(SDK_TARGET_NAME_W L"APBridge", L"APWorldMaker", L"0.2.0", SPI_GAME_SDK_TARGET, SPI_VERSION_ANY);
SPI_PLUGINSIDE_POSTLOAD;
SPI_PLUGINSIDE_ASYNCATTACH;

SPI_IMPLEMENT_ATTACH {
    LESDK::Initializer init{InterfacePtr, SDK_TARGET_NAME_A "APBridge"};
    Common::SetupDefaultLogger(SDK_TARGET_NAME_A, "APBridge");
    Common::InitializeRequiredGlobals(init);
    auto* target = init.ResolveTyped<ProcessEvent>(BUILTIN_PROCESSEVENT_RVA);
    CHECK_RESOLVED(target);
    Original = reinterpret_cast<ProcessEvent*>(init.InstallHook("UObject::ProcessEvent", target, Hook));
    CHECK_RESOLVED(Original);
#if LE3AP_CAREER_TRACE
    static_assert(!LE3AP_DELIVERY_DEV, "Career tracing must not include development delivery writes");
    CareerObserver::ResolveTargets();
    auto* internal = init.ResolveTyped<CareerObserver::Internal>(BUILTIN_PROCESSINTERNAL_RVA);
    auto* call = init.ResolveTyped<CareerObserver::CallFunction>(BUILTIN_CALLFUNCTION_RVA);
    CHECK_RESOLVED(internal);
    CHECK_RESOLVED(call);
    CareerObserver::OriginalInternal = reinterpret_cast<CareerObserver::Internal*>(
        init.InstallHook("UObject::ProcessInternal", internal, CareerObserver::HookInternal));
    CHECK_RESOLVED(CareerObserver::OriginalInternal);
    CareerObserver::OriginalCall = reinterpret_cast<CareerObserver::CallFunction*>(
        init.InstallHook("UObject::CallFunction", call, CareerObserver::HookCall));
    CHECK_RESOLVED(CareerObserver::OriginalCall);
#endif
    HMODULE self = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
        reinterpret_cast<LPCWSTR>(&Serve), &self)) return false;
    std::thread(Serve).detach();
    LEASI_INFO("LE3 Archipelago research bridge attached; development delivery enabled={}", LE3AP_DELIVERY_DEV);
    return true;
}

SPI_IMPLEMENT_DETACH {
    LEASI_UNUSED(InterfacePtr);
    Stopping.store(true);
    Common::ShutdownLogger();
    return true;
}
