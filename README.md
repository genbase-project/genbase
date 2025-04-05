<p align="center">
  <img src="https://raw.githubusercontent.com/genbase-project/genbase/refs/heads/main/docs/public/logo.png" width="150" alt="Genbase Logo">
</p>

<h1 align="center">Genbase</h1>

<p align="center">
  <strong>The Operating System for Modular AI Agents</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License"></a>
  <a href="https://github.com/genbase-project/genbase/stargazers"><img src="https://img.shields.io/github/stars/genbase-project/genbase.svg?style=social&label=Star" alt="GitHub Stars"></a>
  <!-- Add Build Status, Docs, Discord badges when available -->
</p>

---

**Genbase is an open-source platform designed to help you build, manage, and orchestrate complex AI systems.** Instead of building monolithic AI applications, Genbase enables you to create sophisticated solutions by composing specialized, reusable AI agents that can securely collaborate.

Building powerful AI systems often involves integrating diverse capabilities – managing databases, generating code, interacting with external APIs, analyzing data, and more. Doing this reliably, securely, and without reinventing the wheel is challenging.

Genbase tackles this complexity by introducing **Kits**: self-contained, versioned blueprints that package specific AI functionalities. A Kit might contain specialized agent logic, Python tools (Actions), configuration, dependencies, and even initial workspace files. These Kits can be shared and reused across projects.

You instantiate Kits as **Modules** within your **Project**. Each Module runs as a managed component with its own state and secure execution environment. Crucially, Modules can be interconnected:
*   They can establish **Relationships** (`Connection`, `Context`) to understand dependencies.
*   They can securely **Provide** resources like workspace access or specific Actions to other Modules that need them.

This modular, collaborative approach allows you to build systems where specialized agents work together. For example, a code generation Module could use an Action provided by a database management Module to fetch schema information before writing application code.

Humans remain central to the process. Genbase Studio provides an intuitive interface to manage your ecosystem, interact with agents through defined **Profiles** (specific operational modes like 'initialize' or 'maintain'), monitor progress, and guide the overall system.

![Genbase Studio Interface - Module View](https://raw.githubusercontent.com/genbase-project/genbase/refs/heads/main/docs/public/module.png)

## Key Highlights

*   **Build with Reusable Blocks:** Package expertise into shareable Kits, drastically reducing redundant development.
*   **Orchestrate Collaboration:** Define how Modules connect and securely share capabilities (`Provide` Workspaces/Actions).
*   **Secure & Isolated Execution:** Run custom Python Actions in sandboxed Docker containers with managed dependencies.
*   **Centralized LLM Access:** Configure your preferred LLM centrally and let Modules access it securely via an OpenAI-compatible gateway using unique API keys.
*   **Human-in-the-Loop Interface:** Manage, monitor, and interact with your AI system through the Genbase Studio web UI.

## Core Concepts

*   **Kit:** A shareable blueprint for an AI capability (code, config, data, profile). Defined by `kit.yaml`.
*   **Module:** A live instance of a Kit running within a Project, with its own state and connections.
*   **Project:** An organizational container for Modules.
*   **Profile:** A specific task or interaction mode defined for a Module (e.g., `initialize`, `maintain`).
*   **Action:** A Kit-defined Python function executed securely in a container.
*   **Relation:** A defined link between Modules (`Connection` or `Context`).
*   **Provide:** Mechanism for one Module to grant another access to its `Workspace` or specific `Actions`.

*(For more details, see the [Core Concepts Documentation](link-to-docs/concepts))*

## Getting Started 🚀

The recommended way to run Genbase is using Docker Compose.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/genbase-project/genbase.git
    cd genbase
    ```

2.  **Prepare Environment Files:** Copy the templates. **You must edit `engine/.env`**.
    ```bash
    cp docker/.env.template docker/.env
    cp engine/.env.template engine/.env
    cp studio/.env.template studio/.env
    ```

3.  **Configure the Engine:** Edit `engine/.env`:
    *   **Required:** Set at least one LLM API key (e.g., `OPENAI_API_KEY=sk-...`).
    *   **Required:** Set `ADMIN_PASSWORD` for the initial 'admin' user.
    *   **Required:** Configure `DATABASE_URL` for PostgreSQL.
    *   **Required:** Set `AUTH_SECRET` for JWT security.
    ```bash
    nano engine/.env  # Or your preferred text editor
    ```

4.  **Make Scripts Executable:**
    ```bash
    chmod +x scripts/*.sh
    ```

5.  **Start Genbase:**
    ```bash
    ./scripts/docker-run.sh up
    ```
    *(Wait for services to start and migrations to complete).*

6.  **Access Genbase:**
    *   **Studio UI:** [http://localhost:5173](http://localhost:5173)
    *   **Engine API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
    *   Log in with username `admin` and the password you set.

### Running Locally (Development)

1.  Ensure Python 3.11+ and Node.js 18+ are installed.
2.  Follow steps 1-3 above.
3.  Run the local development script:
    ```bash
    ./scripts/run-local.sh
    ```

## Quick Demo 💡

1.  Log in to the Studio.
2.  Ensure the `default` project is selected (or create one).
3.  Go to the **Registry** tab, find a Kit, and click **Install Kit**.
4.  Go to the **Modules** tab and click **Create Module**.
5.  Select the installed Kit, name your module, and create it.
6.  Select your new module in the tree.
7.  In the bottom panel, choose a **Profile** and start chatting with the agent!

## Documentation 📚

*   [Getting Started Guide](https://docs.genbase.io/docs/overview/getting-started)
*   [Core Concepts Explained](https://docs.genbase.io/docs/overview/concepts)
*   [Architecture Details](https://docs.genbase.io/docs/overview/architecture)
*   [Creating Kits](https://docs.genbase.io/docs/development/creating-kits)

## Contributing 🤝

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details.

## Community & Support 💬

*   **GitHub Issues:** [Report bugs or request features](https://github.com/genbase-project/genbase/issues)
*   **GitHub Discussions:** [Ask questions and share ideas](https://github.com/genbase-project/genbase/discussions)

## License

Genbase is distributed under the terms of the [Apache License 2.0](LICENSE).