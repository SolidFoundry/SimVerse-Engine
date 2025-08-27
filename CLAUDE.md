# 与Claude Code在SimVerse-Engine项目上的协作指南

你好，Claude Code。本文件是我们在这个仓库进行高效协作的核心指南。请在每次与我交互时，都遵循以下规则。

## 1. 项目概述 (Project Overview)

SimVerse-Engine是一个用于实时模拟的轻量级2D引擎，采用模块化设计。

*   **后端 (`backend/`)**: Python FastAPI应用。
*   **前端 (`frontend/`)**: 纯粹的HTML/CSS/JS客户端。
*   **控制器 (`controller/`)**: Python脚本。

## 2. 核心：开发环境与命令 (Development Environment & Commands)

**本项目使用Python内置的`venv`模块创建名为`.venv`的虚拟环境进行依赖管理。所有Python命令都应在激活虚拟环境后执行。**

*   **环境准备 (由我手动完成):**
    1.  `python -m venv .venv`
    2.  (激活虚拟环境)
    3.  `pip install -r requirements.txt`

*   **启动后端开发服务器 (在激活的venv中):**
    ```bash
    uvicorn backend.main:app --reload
    ```

*   **运行模拟控制器 (在激活的venv中):**
    ```bash
    python controller/controller.py
    ```

*   **管理Python依赖:**
    *   当我需要添加新依赖时，我会手动执行 `pip install package-name`，然后使用 `pip freeze > requirements.txt` 来更新依赖文件。
    *   **你(Claude Code)只需要在代码中使用了新的库时，提醒我需要安装它即可。**

## 3. 代码风格与注释要求 (Code Style & Comments)

*   **Python:** 严格遵循PEP 8，鼓励使用类型提示(Type Hints)。
*   **注释:** 所有代码和注释**必须使用中文**。注释的核心是解释“**为什么**”这么设计（设计意图），而不是简单地描述“**这行代码做了什么**”。

## 4. 重要注意事项 (Important Notes)

*   **尊重现有架构：** 在修改代码时，请严格遵守后端-前端-控制器的三层解耦架构。
*   **安全第一：** 任何代码修改都不能硬编码敏感信息。

## 5. 你的角色 (Your Role)

你是我们的高级软件工程师。当我对你提出开发需求时，**我期望你直接提供修改后的、完整的代码文件内容，或者清晰的`diff`格式修改建议**。

感谢你的协作！