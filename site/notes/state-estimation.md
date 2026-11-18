---
title: "Estimate robot state from noisy measurements"
topic: "Perception and estimation"
order: "043"
description: "Derive predict and update, inspect observability, and replay a Kalman filter with missing and spurious fixes."
prerequisites: "Basic probability, matrix multiplication, Python, and sensor calibration."
minutes: 65
---

## Recover a quantity no sensor sees reliably

An indoor rover follows a straight aisle in simulation. Wheel encoders give a displacement estimate each tick, even when the far wall is occluded. An occasional range to a surveyed wall gives an independent position fix where the wall is visible and the rover faces it. Wheel increments accumulate error. Wall fixes are noisy, sparse, and sometimes refer to the wrong surface. The estimator should use both and expose the uncertainty it has about its answer.

Define your state by what must be inferred. The lab needs one coordinate `x` in meters along the aisle in a fixed reference frame. For a rover moving freely on a level floor, a useful pose state is `(x, y, yaw)`, possibly extended with velocity or gyro bias. A sensor measurement is a function of that state. For a surveyed wall perpendicular to the aisle at coordinate `L`, the range from a forward-facing sensor at offset `d` is approximately `L - x - d` under the lab geometry. Convert that range to `x` once and keep the measurement variance in m². A false wall association can give a very precise answer to the wrong question.

## Bayes filtering: propagate, then condition

A belief assigns probabilities to possible states. At each step, use a motion model `p(x_k | x_prev, u_k)` to spread the previous belief over the new state. Here `u_k` denotes the observed wheel increment used as a motion input. When a measurement arrives, multiply the predicted belief by its likelihood `p(z_k | x_k)` and normalize. The factorization assumes that the chosen state contains the history needed by the motion model, and that the measurement is conditionally independent of earlier data given that state and the measurement model.

```text
previous posterior -- motion input and process noise --> predicted belief
                                                              |
measurement at the same time --> compare with predicted value |
                                                              v
                            accepted measurement --> updated posterior
                            missing or gated out  --> keep prediction
```

In a linear model with independent Gaussian noise, the **Kalman filter** propagates the mean and covariance, which fully describe a Gaussian belief. Write `P` for the covariance of the state error. Its diagonal holds variances and its off-diagonal entries capture how errors vary together. For example, an uncertain heading causes growing lateral position uncertainty as a rover travels. Use a prediction model `x = F x_prev + B u + w`, and a measurement model `z = H x + v`. `Q` and `R` are the covariances of `w` and `v`. Choose `Q` for the modeled step and actual elapsed time. An encoder-derived pose and velocity can share wheel evidence, so naively treating both as independent updates can overstate confidence. [Welch and Bishop, An Introduction to the Kalman Filter](https://www.cs.cmu.edu/~motionplanning/papers/sbp_papers/kalman/welch_intro_kalman.pdf)

```text
Prediction: x_pred = F x_prev + B u        P_pred = F P_prev F^T + Q
Innovation: e = z - H x_pred              S = H P_pred H^T + R
Gain:       K = P_pred H^T S^-1
Update:     x = x_pred + K e
            P = (I - K H) P_pred (I - K H)^T + K R K^T
```

The innovation `e` is the discrepancy you could observe at the time of the update. `S` is the covariance you expect for that discrepancy. In one dimension with `H = 1`, predicted variance `0.04 m²` and measurement variance `0.01 m²` give `K = 0.8`. A fix 0.10 m ahead shifts the estimate 0.08 m forward. The updated variance is `0.008 m²`. In matrix code use a linear solve for the gain. The displayed covariance update, called the Joseph form, makes its two uncertainty contributions explicit. In the scalar case they simplify to `(1 - K) P_pred` for this gain.

## Know what the data can determine

**Observability** asks whether different candidate states can be distinguished by the outputs over time. For a constant linear model, stack `H`, `HF`, `HF²`, and further powers up to one less than the state dimension. Full column rank means all state directions are observable over that window under the model. For a planar rover, wheel increments alone give no anchor for absolute starting location. In a straight, uniform corridor, ranges to side walls do not constrain translation along those walls. More samples of the same geometry can still leave that direction unobservable. A covariance that shrinks along it calls for a review of the model, priors, and correlations.

For nonlinear motion or measurements, the **extended Kalman filter** (EKF) uses the nonlinear functions to predict the mean and measurement. It uses their local derivatives, or Jacobians, in the covariance calculations. For a simple forward step `d`, the increments `d cos(yaw)` and `d sin(yaw)` couple heading error to position error. Linearization is local. Start with a sensible initial estimate, wrap angular innovations to a consistent interval, and test large initial errors and turn trajectories. A particle filter can represent multiple pose hypotheses in a symmetric hallway, at greater computational cost and with a need to preserve enough samples near plausible poses. [Welch and Bishop, extended Kalman filter](https://www.cs.cmu.edu/~motionplanning/papers/sbp_papers/kalman/welch_intro_kalman.pdf)

## Lab: replay noisy increments and sparse wall fixes

Save as `sensing-fusion.py` and run `python sensing-fusion.py`. This fixture starts from a known position, steps every 0.1 s, and uses exact simulation truth to generate fixes in the same fixed reference frame. The known wall geometry is already accounted for in the fixes. It drops scheduled fixes at steps 25 through 35 and adds 0.80 m to the fix at step 45. Both filters see the same data. The gate rejects updates when squared innovation divided by innovation variance exceeds 9. For a correctly modeled scalar Gaussian innovation, that is a three-standard-deviation rule. The statistic is called normalized innovation squared, or NIS, and has no units.

```python
from math import sqrt
from random import Random
from statistics import mean

rng = Random(43)
q, r = 0.035**2, 0.06**2  # process variance per tick, fix variance (m²)
rows = []
for k in range(1, 101):
    truth = k * 0.06
    wheel = 0.06 + rng.gauss(0, sqrt(q))
    fix = None
    if k % 5 == 0 and not 25 <= k <= 35:
        fix = truth + rng.gauss(0, sqrt(r)) + (0.80 if k == 45 else 0)
    rows.append((k, truth, wheel, fix))


def replay(gate):
    x = p = odom = 0.0
    errors, odom_errors, rejected = [], [], []
    for k, truth, wheel, fix in rows:
        odom += wheel
        x, p = x + wheel, p + q
        if fix is not None:
            innovation = fix - x
            s = p + r
            nis = innovation**2 / s
            if nis > gate:
                rejected.append(k)
            else:
                gain = p / s
                x += gain * innovation
                p *= 1 - gain
            if k == 45:
                print(f"step {k}: innovation={innovation:+.3f} m, NIS={nis:.1f}")
        if k in (20, 35):
            print(f"step {k}: posterior sigma={sqrt(p):.3f} m")
        errors.append((x - truth)**2)
        odom_errors.append((odom - truth)**2)
    print(f"RMSE fusion={sqrt(mean(errors)):.3f} m, "
          f"wheel={sqrt(mean(odom_errors)):.3f} m, rejected={rejected}")


for threshold in (float("inf"), 9.0):
    print(f"NIS gate={threshold}")
    replay(threshold)
```

Uncertainty should increase during the dropout, and the gated filter should skip the injected fix. Inspect step 45 before comparing trajectory RMSE. On another seed, a legitimate measurement may exceed the threshold. Gate against the predicted uncertainty and track rejection runs. When innovations stay large, inspect timestamp alignment, transforms, noise assumptions, and data association. Rejecting every fix can allow the estimator to drift indefinitely.

In a project, replay in acquisition order, log pre-gate innovations and `S` by sensor, and compare against independent truth when available. Persistent signed innovation suggests bias or lag. Bursts during turns suggest geometry, timing, or a missing motion term. A filter with frequent large innovations may be underestimating uncertainty. A low RMSE alone cannot establish calibrated covariance. Plot empirical coverage and residual consistency across held-out trajectories, including missing and delayed data. Define whether delayed observations are dropped or integrated through a bounded history with repropagation. Applying an old fix to the present state silently changes the observation model.

## Exercise: model a wheel scale error

Change the wheel increment's mean from 0.06 m to 0.07 m. Which direction should a fix's innovation tend to have after several prediction steps? How could you distinguish scale error from a wall coordinate offset?

<details>
<summary>Check your diagnosis</summary>
<p>The prediction tends to be too far forward, so the fix tends to give a negative innovation. Across independent runs, regress displacement error against distance since a trusted fix. A scale error grows with signed travel. A constant wall coordinate offset shifts absolute fixes. Include stopped intervals, both directions, and independently surveyed references.</p>
</details>

## Exercise: estimate velocity from position fixes

Replace the lab's motion model with constant velocity and state `(x, v)`. With time step `dt`, write the first two rows of the observability matrix for a position-only sensor. What happens with one instantaneous fix?

<details>
<summary>Check the observability argument</summary>
<p>H is [1, 0] and HF is [1, dt]. Their stack has rank two for nonzero dt. Position measurements over time carry information about velocity, though noise and short intervals affect its quality. One instantaneous position fix contributes one direct constraint and cannot determine both unknowns on its own.</p>
</details>

## What to carry forward

- Use a motion model to propagate belief and a measurement model to condition it. Keep states, covariances, frames, and times explicit.
- Check observability before adding state variables. Use innovations, coverage, and independent truth to investigate estimator behavior.
- [Mapping and SLAM](/notes/mapping-and-slam/) extends this reasoning to revisiting places and correcting a trajectory in a global reference frame.
