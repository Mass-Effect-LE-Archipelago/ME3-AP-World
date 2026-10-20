#pragma once
#include "CareerTrace.hpp"

// Included after the SDK headers and Original ProcessEvent trampoline.
// Only the separate career-trace build installs these observer hooks.
namespace CareerObserver {
using Internal = void(UObject*, FFrame*, void*);
using CallFunction = void(UObject*, FFrame*, void*, UFunction*);
Internal* OriginalInternal = nullptr;
CallFunction* OriginalCall = nullptr;
CareerTrace::Buffer Records;
std::atomic<std::uint64_t> NextInvocation{0};
std::array<std::atomic<UFunction*>, 5> Targets{};
std::atomic<unsigned> TargetMask{0};
std::mutex ResolveMutex;
std::atomic<ULONGLONG> NextResolve{0};
thread_local bool Capturing = false;
thread_local unsigned CommitDepth = 0;
thread_local int Origin = -1;
thread_local ABioWorldInfo* CareerWorld = nullptr;

void ResolveTargets() {
    auto const now = GetTickCount64();
    if (TargetMask.load() == 31 || now < NextResolve.load()) return;
    std::unique_lock lock(ResolveMutex, std::try_to_lock);
    if (!lock || now < NextResolve.load()) return;
    NextResolve.store(now + 1000);
    constexpr std::array names{
        L"Function SFXGame.BioSFHandler_NewCharacter.FinalCommit",
        L"Function SFXGame.BioSFHandler_NewCharacter.SetPlotChoices",
        L"Function SFXGame.SFXEngine.CreateCareer",
        L"Function SFXGame.BioGlobalVariableTable.SetNewGamePlotStates",
        L"Function SFXGame.SFXSaveGame.UpdatePlayerSaveRecord"};
    unsigned mask = 0;
    for (std::size_t i = 0; i < names.size(); ++i) {
        if (!Targets[i].load()) Targets[i].store(UObject::FindObject<UFunction>(names[i]));
        if (Targets[i].load()) mask |= 1u << i;
    }
    TargetMask.store(mask);
}

CareerTrace::Method Classify(UStruct* node) {
    if (!node || Capturing) return CareerTrace::Method::None;
    ResolveTargets();
    for (unsigned i = 0; i < Targets.size(); ++i)
        if (Targets[i].load() == node) return static_cast<CareerTrace::Method>(i + 1);
    return CareerTrace::Method::None;
}

void Capture(UObject* context, CareerTrace::Method method, CareerTrace::Route route,
             std::uint64_t invocation, bool leaving) noexcept {
    // Re-entrancy guard covers observer reads only, so original target calls and
    // their nested script calls remain visible. Never mutate function flags.
    Capturing = true;
    try {
        CareerTrace::Record record;
        record.invocation = invocation;
        record.thread = GetCurrentThreadId();
        record.route = route; record.method = method; record.leaving = leaving;
        record.depth = CommitDepth; record.origin = Origin;
        UBioGlobalVariableTable* table = nullptr;
        if (method == CareerTrace::Method::PlotStates && context && !Common::IsDestroyed(context)) {
            table = context->Cast<UBioGlobalVariableTable>();
            if (table) record.table = Common::IsDefaultObject(table) ? 2u : 3u;
        } else if (Live(CareerWorld)) {
            auto* getter = UObject::FindObject<UFunction>(L"Function SFXGame.BioWorldInfo.GetGlobalVariables");
            if (getter && (getter->FunctionFlags & 0x400)) {
                struct Params { UBioGlobalVariableTable* value = nullptr; } parameters;
                Original(CareerWorld, getter, &parameters, nullptr);
                table = parameters.value;
                if (table) record.table = 1;
            }
        }
        if (table && !Common::IsDestroyed(table)) {
            auto* getter = UObject::FindObject<UFunction>(L"Function SFXGame.BioGlobalVariableTable.GetBool");
            if (getter && (getter->FunctionFlags & 0x400)) {
                for (unsigned i = 0; i < CareerTrace::Plots.size(); ++i) {
                    struct Params { int index, value = 0; } parameters{CareerTrace::Plots[i]};
                    Original(table, getter, &parameters, nullptr);
                    record.valid |= 1u << i;
                    if (parameters.value) record.values |= 1u << i;
                }
            }
        }
        Records.append(record);
    } catch (...) { /* Observational failures must not replace the game's call. */ }
    Capturing = false;
}

struct Observation {
    UObject* context;
    CareerTrace::Method method;
    CareerTrace::Route route;
    std::uint64_t invocation = 0;
    Observation(UObject* object, UStruct* node, CareerTrace::Route path)
        : context(object), method(Classify(node)), route(path) {
        if (method == CareerTrace::Method::None) return;
        if (method == CareerTrace::Method::FinalCommit) {
            if (CommitDepth++ == 0 && Live(context)) {
                auto* handler = context->Cast<UBioSFHandler_NewCharacter>();
                if (handler) { Origin = handler->m_nDataOrigin; CareerWorld = handler->oWorldInfo; }
            }
        }
        invocation = ++NextInvocation;
        Capture(context, method, route, invocation, false);
    }
    ~Observation() {
        if (method == CareerTrace::Method::None) return;
        Capture(context, method, route, invocation, true);
        if (method == CareerTrace::Method::FinalCommit && --CommitDepth == 0) { Origin = -1; CareerWorld = nullptr; }
    }
};

void HookInternal(UObject* context, FFrame* frame, void* result) {
    Observation observe(context, frame ? frame->Node : nullptr, CareerTrace::Route::Internal);
    OriginalInternal(context, frame, result);
}
void HookCall(UObject* context, FFrame* frame, void* result, UFunction* function) {
    Observation observe(context, function, CareerTrace::Route::CallFunction);
    OriginalCall(context, frame, result, function);
}
}
