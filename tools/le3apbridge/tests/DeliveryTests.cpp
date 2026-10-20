#include "../Delivery.hpp"
#include <functional>
#include <iostream>
#include <map>

namespace {
int checks = 0;
void require(bool value, char const* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
struct Host {
    std::map<int, int> ints;
    int credits = 100, maximum = 10000, adjustments = 0;
    bool ending = false, player = true, failCursor = false, failGrant = false;
    int read(int index) { return ints[index]; }
    void write(int index, int value) {
        ints[index] = value;
        if (index == Delivery::Base + 2 && failCursor) { failCursor = false; throw std::runtime_error("simulated_postwrite_error"); }
    }
    bool completed() { return ending; }
    Delivery::Wallet wallet() {
        if (!player) throw std::runtime_error("noplayer");
        return {credits, maximum};
    }
    void adjustCredits(int amount) { ++adjustments; credits += amount; if (failGrant) ++credits; }
    void restoreCredits(int value) { credits = value; }
};
Delivery::Request parse(std::string const& text) {
    Delivery::Request request;
    auto error = Delivery::parse(text, request);
    if (!error.empty()) throw std::runtime_error(error);
    return request;
}
std::string const Seed(64, 'f'), History(64, '1'), Other(64, '2');
Delivery::Request bind() { return parse("DEV_BIND " + Seed + " " + History + " RESEARCH_ONLY"); }
Delivery::Request credit(int index = 0) { return parse("DEV_TXN " + Seed + " " + History + " " + std::to_string(index) + " CREDITS 1000"); }
bool throws(std::function<void()> const& action) { try { action(); return false; } catch (std::runtime_error const&) { return true; } }
}
int main() {
    try {
        Host host;
        require(Delivery::execute(parse("DEV_SESSION"), host) == "OK 1 research_only unbound 0", "unbound session");
        require(Delivery::execute(credit(), host) == "ERR identity", "unbound mutation refused");
        require(Delivery::execute(bind(), host) == "OK bound research_only", "bind succeeds");
        auto state = Delivery::load(host);
        require(state.bound && Delivery::hex(state.identity) == Seed, "full SHA digest survives signed storage");
        require(host.ints[Delivery::Base + 4] == -1, "high digest bits are preserved");
        require(Delivery::execute(bind(), host) == "ERR bound", "rebinding refused");
        auto before = host;
        require(Delivery::execute(credit(1), host) == "ERR gap 0", "gap refused");
        require(Delivery::execute(credit(), host) == "OK 1 1000 applied", "credit applies");
        require(host.credits == 1100 && Delivery::load(host).cursor == 1, "credit and cursor updated");
        require(Delivery::execute(credit(), host) == "OK 1 0 done", "lost-reply retry skipped");
        require(host.credits == 1100 && host.adjustments == 1, "retry does not grant twice");
        auto saved = host;
        host = before; // Loading the pre-delivery save replays just its suffix.
        require(Delivery::execute(credit(), host) == "OK 1 1000 applied", "old-save replay");
        require(host.credits == saved.credits && Delivery::load(host).cursor == 1, "old-save balance correct");
        auto wrong = parse("DEV_TXN " + Other + " " + History + " 0 CREDITS 1000");
        require(Delivery::execute(wrong, host) == "ERR identity", "wrong seed rejected even for old index");
        wrong = parse("DEV_TXN " + Seed + " " + Other + " 1 COUNTER");
        require(Delivery::execute(wrong, host) == "ERR identity", "wrong history rejected");
        Host switched; Delivery::execute(parse("DEV_BIND " + Other + " " + History + " RESEARCH_ONLY"), switched);
        require(Delivery::execute(credit(), switched) == "ERR identity", "queued request checked against newly loaded save");
        host.maximum = host.credits + 20;
        require(Delivery::execute(credit(1), host) == "OK 2 20 applied", "partial cap explicitly consumed");
        require(Delivery::execute(credit(2), host) == "OK 3 0 applied", "full cap cannot block later intel");
        host.player = false;
        require(Delivery::execute(parse("DEV_TXN " + Seed + " " + History + " 3 COUNTER"), host) == "OK 4 0 applied", "counter does not need wallet");
        require(throws([&] { Delivery::execute(credit(4), host); }), "missing pawn refused");
        require(Delivery::load(host).cursor == 4, "missing pawn does not consume");
        host.player = true; host.maximum = 10000; host.failCursor = true;
        int prior = host.credits;
        require(throws([&] { Delivery::execute(credit(4), host); }), "postwrite commit failure surfaced");
        require(host.credits == prior && Delivery::load(host).cursor == 4, "failed commit restores credit and cursor");
        host.failGrant = true;
        require(throws([&] { Delivery::execute(credit(4), host); }), "unexpected grant effect refused");
        require(host.credits == prior && Delivery::load(host).cursor == 4, "unexpected effect rolled back");
        Host ended; ended.ending = true;
        require(Delivery::execute(bind(), ended) == "ERR completed_career", "completed save not bound");
        Host collision; collision.ints[Delivery::Base + 7] = 12;
        require(throws([&] { Delivery::execute(bind(), collision); }), "partial/colliding block not overwritten");
        for (auto const& text : std::vector<std::string>{"DEV_TXN x y 0 COUNTER", "DEV_BIND x y RESEARCH_ONLY", "DEV_WALLET extra",
                "DEV_SESSION extra", "DEV_TXN " + Seed + " " + History + " -1 CREDITS 1000",
                "DEV_TXN " + Seed + " " + History + " 0 CREDITS 0",
                "DEV_TXN " + Seed + " " + History + " 0 CREDITS 1000 extra",
                "DEV_TXN " + Seed + " " + History + " 0 WEAPON 9"}) {
            Delivery::Request request;
            require(!Delivery::parse(text, request).empty(), "malformed/unsupported command refused");
        }
        // Cerberus HQ gate: requirement set at bind, intel counted per indexed item.
        auto intel = [](int index) { return parse("DEV_TXN " + Seed + " " + History + " " + std::to_string(index) + " INTEL"); };
        Host fresh;
        require(!Delivery::gateBlocks(fresh) && Delivery::execute(parse("DEV_GATE"), fresh) == "OK 0 0 unbound", "unbound career never gated");
        require(!Delivery::gateBlocks(host), "research binding without requirement is open");
        require(Delivery::execute(parse("DEV_BIND " + Seed + " " + History + " RESEARCH_ONLY 2"), fresh) == "OK bound research_only", "bind with requirement");
        require(Delivery::gateBlocks(fresh) && Delivery::execute(parse("DEV_GATE"), fresh) == "OK 2 0 closed", "gate starts closed");
        require(Delivery::execute(intel(0), fresh) == "OK 1 0 applied", "first intel");
        require(Delivery::execute(intel(0), fresh) == "OK 1 0 done" && Delivery::load(fresh).received == 1, "intel retry not double counted");
        require(Delivery::gateBlocks(fresh), "one of two intel still closed");
        auto oneIntel = fresh;
        require(Delivery::execute(credit(1), fresh) == "OK 2 1000 applied", "credits do not count as intel");
        require(Delivery::execute(intel(2), fresh) == "OK 3 0 applied" && !Delivery::gateBlocks(fresh), "enough intel opens gate");
        require(Delivery::execute(parse("DEV_GATE"), fresh) == "OK 2 2 open", "gate reports open");
        require(Delivery::gateBlocks(oneIntel), "older save keeps its own intel count");
        fresh.failCursor = true;
        require(throws([&] { Delivery::execute(intel(3), fresh); }), "intel commit failure surfaced");
        require(Delivery::load(fresh).received == 2 && Delivery::load(fresh).cursor == 3, "failed intel rolled back");
        Host corrupt = oneIntel; corrupt.ints[Delivery::IntelReceived] = 5;
        require(Delivery::gateBlocks(corrupt), "inconsistent gate state fails closed");
        Delivery::Request request;
        require(!Delivery::parse("DEV_BIND " + Seed + " " + History + " RESEARCH_ONLY 1001", request).empty(), "oversized requirement refused");
        require(!Delivery::parse("DEV_GATE extra", request).empty(), "gate query takes no arguments");
        std::cout << "DeliveryTests: " << checks << " checks passed\n";
        return 0;
    } catch (std::exception const& error) { std::cerr << "FAILED: " << error.what() << '\n'; return 1; }
}
