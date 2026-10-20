#pragma once
#include <array>
#include <charconv>
#include <cstdint>
#include <mutex>
#include <sstream>
#include <string>
#include <vector>

namespace CareerTrace {
// Protocol enum values are stable. Records hold no game pointers or names.
enum class Method : unsigned { None, FinalCommit, PlotChoices, CreateCareer, PlotStates, SavePlayerRecord };
enum class Route : unsigned { Event, Internal, CallFunction };
struct Record {
    std::uint64_t sequence = 0, invocation = 0;
    unsigned thread = 0;
    Route route = Route::Event;
    Method method = Method::None;
    bool leaving = false;
    unsigned depth = 0;
    int origin = -1;
    // 0 unavailable, 1 world-accessor table, 2 default context table, 3 instance context table.
    unsigned table = 0, valid = 0, values = 0;
};
constexpr std::array<int, 4> Plots{13827, 13828, 13940, 13939};
constexpr unsigned Capacity = 128;

class Buffer {
    std::array<Record, Capacity> records{};
    std::uint64_t latest = 0;
    std::mutex mutex;
public:
    void append(Record record) {
        std::lock_guard lock(mutex);
        record.sequence = ++latest;
        records[static_cast<std::size_t>((latest - 1) % Capacity)] = record;
    }
    std::string page(std::uint64_t after, unsigned limit, unsigned targetMask) {
        std::lock_guard lock(mutex);
        auto const oldest = latest > Capacity ? latest - Capacity + 1 : latest ? 1 : 0;
        std::vector<Record> selected;
        // Compare rather than after+1 to avoid overflow for UINT64_MAX.
        if (oldest) for (auto sequence = oldest; sequence <= latest && selected.size() < limit; ++sequence) {
            if (sequence > after) selected.push_back(records[static_cast<std::size_t>((sequence - 1) % Capacity)]);
        }
        std::string result = "OK 1 career_trace_readonly " + std::to_string(targetMask) + " "
            + std::to_string(oldest) + " " + std::to_string(latest) + " " + std::to_string(selected.size());
        for (auto const& r : selected) {
            result += " " + std::to_string(r.sequence) + ":" + std::to_string(r.invocation)
                + ":" + std::to_string(r.thread) + ":" + std::to_string(static_cast<unsigned>(r.route))
                + ":" + std::to_string(static_cast<unsigned>(r.method)) + ":" + std::to_string(r.leaving)
                + ":" + std::to_string(r.depth) + ":" + std::to_string(r.origin)
                + ":" + std::to_string(r.table) + ":" + std::to_string(r.valid) + ":" + std::to_string(r.values);
        }
        return result;
    }
};

inline bool parse(std::string const& message, std::uint64_t& after, unsigned& limit) {
    std::istringstream stream(message);
    std::string command, cursor, count, extra;
    if (!(stream >> command >> cursor >> count) || command != "CAREER_TRACE" || stream >> extra) return false;
    auto read = [](std::string const& text, auto& value) {
        auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
        return error == std::errc{} && end == text.data() + text.size();
    };
    return read(cursor, after) && read(count, limit) && limit >= 1 && limit <= 64;
}
}
