# Runtime Service Architecture

## Overview

TITAN uses a separated architecture for its runtime execution environment to ensure robustness, fault tolerance, and a clean separation of concerns.

The architecture splits execution into two primary concepts:
1. **RuntimeEngine**: The core execution loop (application logic).
2. **RuntimeService**: The service lifecycle wrapper (management logic).

## RuntimeEngine

The `RuntimeEngine` (located in `titan/runtime/runtime.py`) is responsible for running the continuous loop that ticks the scheduler, handles broker connections, monitors health, and executes pipelines. 

In the latest architecture, the `RuntimeEngine.start()` method is **blocking**. It runs an infinite `while` loop that only terminates when explicitly stopped or interrupted. This guarantees the runtime does not exit prematurely when running in a detached mode or daemon process.

## RuntimeService

The `RuntimeService` (located in `titan/runtime/service.py`) is a pure application logic wrapper around the `RuntimeEngine`. It provides a clean interface for external controllers to start, stop, restart, and monitor the engine without needing to understand its internal threading or loop mechanics.

## LocalTransport (IPC)

Because the `RuntimeEngine` is blocking, external processes (like the TITAN CLI) cannot interact with it directly if it was started in a detached process (e.g. `titan paper start --detach`). 

To bridge this gap, TITAN implements a lightweight Inter-Process Communication (IPC) layer using local TCP sockets:

- **LocalTransportServer**: A daemon thread started just before the `RuntimeEngine` loop. It listens on `127.0.0.1:50555` for incoming commands.
- **LocalTransport**: The client used by the CLI to send JSON-encoded commands (e.g., `status`, `stop`, `paper_status`) to the running server.

This design ensures:
- **No Background Polling Hacks**: We don't rely on continuously polling lockfiles or JSON dumps.
- **No Broker Leakage**: The CLI does not instantiate its own broker connection to read live data; it queries the live engine.
- **Single Source of Truth**: The running `RuntimeEngine` holds the state in memory, and the CLI retrieves it via IPC.

## Lifecycle Example (Paper Trading)

1. User runs `titan paper start --detach`
2. The CLI spawns a new background Python process and exits.
3. The background process initializes the `RuntimeEngine` and `RuntimeService`.
4. It starts the `LocalTransportServer` on port 50555.
5. It calls `RuntimeEngine.start()`, blocking the main thread and beginning the trading loop.
6. The user runs `titan paper status`.
7. The CLI connects to `127.0.0.1:50555` using `LocalTransport`, requests `paper_status`, and prints the response.
