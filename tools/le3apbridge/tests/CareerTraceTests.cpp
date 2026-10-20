#include "../CareerTrace.hpp"
#include <iostream>
#include <stdexcept>

int main() {
    unsigned checks = 0;
    auto check = [&](bool value) { ++checks; if (!value) throw std::runtime_error("Career trace check failed"); };
    CareerTrace::Buffer buffer;
    check(buffer.page(0, 64, 31) == "OK 1 career_trace_readonly 31 0 0 0");
    CareerTrace::Record entry;
    entry.invocation = 7; entry.thread = 42; entry.method = CareerTrace::Method::PlotChoices;
    entry.route = CareerTrace::Route::Internal; entry.depth = 1; entry.origin = 0;
    entry.table = 1; entry.valid = 15; entry.values = 6;
    buffer.append(entry);
    entry.leaving = true; entry.values = 9; buffer.append(entry);
    auto first = buffer.page(0, 1, 31);
    check(first == "OK 1 career_trace_readonly 31 1 2 1 1:7:42:1:2:0:1:0:1:15:6");
    auto second = buffer.page(1, 64, 31);
    check(second == "OK 1 career_trace_readonly 31 1 2 1 2:7:42:1:2:1:1:0:1:15:9");
    check(buffer.page(2, 64, 31) == "OK 1 career_trace_readonly 31 1 2 0");
    check(buffer.page(UINT64_MAX, 64, 31) == "OK 1 career_trace_readonly 31 1 2 0");
    for (unsigned i = 0; i < CareerTrace::Capacity; ++i) buffer.append(entry);
    auto overflow = buffer.page(0, 1, 31);
    check(overflow.starts_with("OK 1 career_trace_readonly 31 3 130 1 3:"));
    check(buffer.page(129, 64, 31).starts_with("OK 1 career_trace_readonly 31 3 130 1 130:"));
    std::uint64_t after = 0; unsigned limit = 0;
    check(CareerTrace::parse("CAREER_TRACE 0 64", after, limit) && after == 0 && limit == 64);
    check(CareerTrace::parse("CAREER_TRACE 18446744073709551615 1", after, limit) && after == UINT64_MAX);
    for (auto bad : {"CAREER_TRACE", "CAREER_TRACE 0", "CAREER_TRACE -1 1", "CAREER_TRACE +1 1",
                     "CAREER_TRACE 1 0", "CAREER_TRACE 1 65", "CAREER_TRACE 1 1 extra",
                     "CAREER_TRACE 18446744073709551616 1", "CAREER_TRACE 0 4294967296", "OTHER 0 1"})
        check(!CareerTrace::parse(bad, after, limit));
    std::cout << checks << " career trace checks passed\n";
}
