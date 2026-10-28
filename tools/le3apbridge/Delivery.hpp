#pragma once
// SDK-independent development delivery contract. No generic plot-write command.
#include <algorithm>
#include <array>
#include <bit>
#include <charconv>
#include <cstdint>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "Weapons.hpp"

namespace Delivery {
constexpr int Base = 0x4D336000; // Sparse integer-map keys, never bool-array indices.
constexpr int Slots = 24;
constexpr int Marker = 0x4D334150;
// Cerberus HQ gate fields in formerly reserved slots; zero means no gate.
constexpr int IntelRequired = Base + 20, IntelReceived = Base + 21;
constexpr int MaxIntel = 1000;
// Missed-checks salvage: plot bools (conditionals cannot read the sparse int keys above 250000). The mod's store row
// for mission k shows while TierBool + tier and AvailBool + k are set and BoughtBool + k is clear; buying sets BoughtBool + k.
constexpr int MaxSalvage = 40, MaxTier = 4;
constexpr int BoughtBool = 26000, AvailBool = BoughtBool + MaxSalvage, TierBool = AvailBool + MaxSalvage;
constexpr int SalvageBoolEnd = TierBool + MaxTier + 1;
using Digest = std::array<std::uint32_t, 8>;
enum class Op { Session, Wallet, Gate, Bind, Counter, Credits, Intel, Weapon, Salvage };
struct Request {
    Op op = Op::Session;
    Digest identity{}, history{};
    int index = 0, amount = 0, required = 0;
    std::vector<int> caps; // Salvage: tier in amount
};
struct State { bool bound = false; Digest identity{}, history{}; int cursor = 0, required = 0, received = 0; };
struct Wallet { int credits, maximum; };

inline bool digest(std::string const& text, Digest& result) {
    if (text.size() != 64) return false;
    bool nonzero = false;
    for (int i = 0; i < 8; ++i) {
        auto* first = text.data() + i * 8;
        auto [end, error] = std::from_chars(first, first + 8, result[i], 16);
        if (error != std::errc{} || end != first + 8) return false;
        nonzero |= result[i] != 0;
    }
    return nonzero;
}
inline std::string hex(Digest const& value) {
    constexpr char digits[] = "0123456789abcdef";
    std::string result;
    for (auto word : value) for (int shift = 28; shift >= 0; shift -= 4)
        result += digits[(word >> shift) & 15];
    return result;
}
inline bool number(std::string const& text, int& result) {
    auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), result);
    return error == std::errc{} && end == text.data() + text.size() && result >= 0;
}
inline std::string parse(std::string const& text, Request& request) {
    std::istringstream stream(text);
    std::vector<std::string> words;
    for (std::string word; stream >> word;) words.push_back(word);
    if (words.size() == 1 && words[0] == "DEV_SESSION") { request.op = Op::Session; return ""; }
    if (words.size() == 1 && words[0] == "DEV_WALLET") { request.op = Op::Wallet; return ""; }
    if (words.size() == 1 && words[0] == "DEV_GATE") { request.op = Op::Gate; return ""; }
    if ((words.size() == 4 || words.size() == 5) && words[0] == "DEV_BIND" && words[3] == "RESEARCH_ONLY") {
        request.op = Op::Bind;
        // Optional Crucible Intel requirement for the Cerberus HQ gate; omitted means no gate.
        if (words.size() == 5 && (!number(words[4], request.required) || request.required > MaxIntel)) return "ERR requirement";
        return digest(words[1], request.identity) && digest(words[2], request.history) ? "" : "ERR digest";
    }
    // DEV_SALVAGE <identity> <history> <tier> <cap>...: publish caps, take the bought missions.
    if (words.size() >= 5 && words[0] == "DEV_SALVAGE") {
        if (!digest(words[1], request.identity) || !digest(words[2], request.history)) return "ERR digest";
        if (!number(words[3], request.amount) || request.amount > MaxTier) return "ERR tier";
        if (words.size() - 4 > MaxSalvage) return "ERR salvage_count";
        for (std::size_t i = 4; i < words.size(); ++i) {
            int cap = 0;
            if (!number(words[i], cap) || cap > 1000) return "ERR cap";
            request.caps.push_back(cap);
        }
        request.op = Op::Salvage;
        return "";
    }
    if ((words.size() == 5 || words.size() == 6) && words[0] == "DEV_TXN") {
        if (!digest(words[1], request.identity) || !digest(words[2], request.history)) return "ERR digest";
        if (!number(words[3], request.index) || request.index >= 1000000) return "ERR index";
        if (words.size() == 5 && words[4] == "COUNTER") { request.op = Op::Counter; return ""; }
        if (words.size() == 5 && words[4] == "INTEL") { request.op = Op::Intel; return ""; }
        // WEAPON <id>: id indexes Weapons::Classes (append-only wire contract).
        if (words.size() == 6 && words[4] == "WEAPON" && number(words[5], request.amount)
            && request.amount < static_cast<int>(Weapons::Classes.size())) { request.op = Op::Weapon; return ""; }
        if (words.size() == 6 && words[4] == "CREDITS" && number(words[5], request.amount)
            && request.amount >= 1 && request.amount <= 1000000) { request.op = Op::Credits; return ""; }
    }
    return "ERR badrequest";
}
inline bool writes(Request const& request) {
    return request.op != Op::Session && request.op != Op::Wallet && request.op != Op::Gate;
}

// Host operations execute synchronously on the game thread. write() must read
// back the value; resource adjustment is validated and restored on commit error.
template<class Host> State load(Host& host) {
    std::array<int, Slots> values{};
    bool empty = true;
    for (int i = 0; i < Slots; ++i) { values[i] = host.read(Base + i); empty &= values[i] == 0; }
    if (empty) return {};
    if (values[0] != Marker || values[1] != 1 || values[3] != 1 || values[2] < 0 || values[2] > 1000000)
        throw std::runtime_error("storage_collision_or_partial_binding");
    for (int i = 22; i < Slots; ++i) if (values[i] != 0) throw std::runtime_error("storage_reserved");
    if (values[20] < 0 || values[20] > MaxIntel || values[21] < 0 || values[21] > values[2])
        throw std::runtime_error("storage_gate");
    State state; state.bound = true; state.cursor = values[2];
    state.required = values[20]; state.received = values[21];
    for (int i = 0; i < 8; ++i) {
        state.identity[i] = std::bit_cast<std::uint32_t>(values[4 + i]);
        state.history[i] = std::bit_cast<std::uint32_t>(values[12 + i]);
    }
    if (state.identity == Digest{} || state.history == Digest{}) throw std::runtime_error("storage_digest");
    return state;
}

// True when landing on Cerberus HQ must be refused for the loaded save.
// Unbound careers are never gated; unreadable bound state fails closed.
template<class Host> bool gateBlocks(Host& host) {
    try {
        auto state = load(host);
        return state.bound && state.required > 0 && state.received < state.required;
    } catch (...) { return true; }
}

template<class Host> std::string execute(Request const& request, Host& host) {
    if (request.op == Op::Wallet) {
        auto wallet = host.wallet();
        return "OK " + std::to_string(wallet.credits) + " " + std::to_string(wallet.maximum);
    }
    auto state = load(host);
    if (request.op == Op::Gate) {
        if (!state.bound) return "OK 0 0 unbound";
        return "OK " + std::to_string(state.required) + " " + std::to_string(state.received)
            + (state.required > 0 && state.received < state.required ? " closed" : " open");
    }
    if (request.op == Op::Session) {
        if (!state.bound) return "OK 1 research_only unbound 0";
        return "OK 1 research_only " + hex(state.identity) + " " + hex(state.history) + " " + std::to_string(state.cursor);
    }
    if (request.op == Op::Bind) {
        if (state.bound) return "ERR bound";
        if (host.completed()) return "ERR completed_career";
        try {
            for (int i = 0; i < 8; ++i) {
                host.write(Base + 4 + i, std::bit_cast<int>(request.identity[i]));
                host.write(Base + 12 + i, std::bit_cast<int>(request.history[i]));
            }
            if (request.required) host.write(IntelRequired, request.required);
            host.write(Base + 1, 1); host.write(Base + 3, 1);
            host.write(Base, Marker); // Valid binding marker is committed last.
        } catch (...) {
            for (int i = 0; i < Slots; ++i) host.write(Base + i, 0);
            throw;
        }
        return "OK bound research_only";
    }
    // Validate against the CURRENT loaded save at execution, not enqueue time.
    if (!state.bound || state.identity != request.identity || state.history != request.history) return "ERR identity";
    if (request.op == Op::Salvage) {
        // Availability first, so a store reopened after this step already reflects it; then take each bought flag.
        for (int t = 0; t <= MaxTier; ++t) host.writeBool(TierBool + t, t == request.amount);
        for (int k = 0; k < MaxSalvage; ++k)
            host.writeBool(AvailBool + k, k < static_cast<int>(request.caps.size()) && request.caps[k] > 0);
        std::string result = "OK bought";
        for (int k = 0; k < static_cast<int>(request.caps.size()); ++k)
            if (host.readBool(BoughtBool + k)) {
                host.writeBool(BoughtBool + k, false);
                result += " " + std::to_string(k);
            }
        return result;
    }
    if (request.index < state.cursor) return "OK " + std::to_string(state.cursor) + " 0 done";
    if (request.index > state.cursor) return "ERR gap " + std::to_string(state.cursor);
    int actual = 0;
    if (request.op == Op::Credits) {
        auto wallet = host.wallet();
        if (wallet.credits < 0 || wallet.maximum < wallet.credits) return "ERR wallet";
        actual = (std::min)(request.amount, wallet.maximum - wallet.credits);
        try {
            // Capped credits are consumed, so filler cannot block later intel.
            // Avoid a zero-value resource call and its unrelated hint effects.
            if (actual) host.adjustCredits(actual);
            if (host.wallet().credits != wallet.credits + actual) throw std::runtime_error("credit_effect");
            host.write(Base + 2, state.cursor + 1);
        } catch (...) {
            host.restoreCredits(wallet.credits);
            host.write(Base + 2, state.cursor);
            throw;
        }
    } else if (request.op == Op::Weapon) {
        // Unlock = player variable 1. Already-owned weapons still consume the index (duplicate items are harmless).
        int const before = host.weaponOwned(request.amount);
        try {
            if (!before) host.setWeaponOwned(request.amount, 1);
            if (!host.weaponOwned(request.amount)) throw std::runtime_error("weapon_effect");
            host.write(Base + 2, state.cursor + 1);
        } catch (...) {
            if (!before) host.setWeaponOwned(request.amount, 0);
            host.write(Base + 2, state.cursor);
            throw;
        }
    } else if (request.op == Op::Intel) {
        try {
            host.write(IntelReceived, state.received + 1);
            host.write(Base + 2, state.cursor + 1);
        } catch (...) {
            host.write(IntelReceived, state.received);
            host.write(Base + 2, state.cursor);
            throw;
        }
    } else {
        host.write(Base + 2, state.cursor + 1);
    }
    return "OK " + std::to_string(state.cursor + 1) + " " + std::to_string(actual) + " applied";
}
}
