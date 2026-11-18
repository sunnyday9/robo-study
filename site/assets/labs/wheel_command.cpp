#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <optional>

struct WheelRates {
  double left;
  double right;
};

std::optional<WheelRates> to_wheels(double speed, double yaw_rate) {
  constexpr double radius = 0.05;
  constexpr double track = 0.30;
  constexpr double limit = 5.0;
  if (!std::isfinite(speed) || !std::isfinite(yaw_rate)) {
    return std::nullopt;
  }
  const double left = (speed - track * yaw_rate / 2.0) / radius;
  const double right = (speed + track * yaw_rate / 2.0) / radius;
  if (!std::isfinite(left) || !std::isfinite(right)) {
    return std::nullopt;
  }
  const double scale = std::max({1.0, std::abs(left) / limit, std::abs(right) / limit});
  return WheelRates{left / scale, right / scale};
}

int main() {
  const auto straight = to_wheels(0.20, 0.0);
  assert(straight && std::abs(straight->left - 4.0) < 1e-9);
  assert(std::abs(straight->right - 4.0) < 1e-9);

  const auto turn = to_wheels(0.20, 0.40);
  assert(turn && std::abs(turn->right - 5.0) < 1e-9);
  assert(std::abs(turn->left / turn->right - 2.8 / 5.2) < 1e-9);
  assert(!to_wheels(std::nan(""), 0.0));
  std::cout << "OK: straight, curvature-preserving limit, invalid input\n";
}
