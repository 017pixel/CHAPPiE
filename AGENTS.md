# CHAPPiE Agent Instructions

## Critical Configuration Rules

### 1. Systemd Service Configuration
**Strict Requirement:** When configuring the `chappie-training.service` file for background execution, you **MUST** ensure that `ExecStart` points to `training_daemon.py` and **NOT** `training_loop.py`.

- **Correct:** `ExecStart=... -m Chappies_Trainingspartner.training_daemon`
- **Incorrect:** `ExecStart=... -m Chappies_Trainingspartner.training_loop`

`training_daemon.py` contains the necessary entry point and setup for the headless training process. `training_loop.py` is a library module and cannot be executed directly as a service.

### 2. General Service Reliability
- Ensure `Restart=always` is set to guarantee 24/7 operation.
- Use absolute paths for all executables and working directories in service files.
