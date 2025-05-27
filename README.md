# LiteBoty

LiteBoty 是一个轻量级的 Python 机器人框架，专注于构建基于 Redis 的消息驱动服务。

$LiteBoty = "lite" + "bot" + "y" $

## Features

- 🚀 **轻量级设计，易于使用**：框架的设计注重简洁性，减少了不必要的复杂性，使得开发者可以快速上手。只需少量的代码，就可以创建一个基本的机器人服务。
- 📦 **基于 Redis 的消息订阅发布系统**：利用 Redis 作为消息中间件，实现了可靠的消息传递和广播机制。服务之间可以通过 Redis 进行高效的通信，支持订阅和发布不同类型的消息。
- 🔌 **插件化服务架构 / 微服务架构**：框架支持插件化开发，每个服务可以作为一个独立的插件进行开发和部署。这种微服务架构使得系统具有高度的可扩展性和灵活性，可以根据需求轻松添加或移除服务组件。
- ⚡ **异步消息处理：采用异步编程模型**，提高了系统的并发处理能力。通过 asyncio 库，服务可以同时处理多个消息，避免了阻塞式 I/O 操作，提高了系统的性能和响应速度。
- 🛠 **便捷的 CLI 工具**：提供了命令行工具，方便开发者进行项目的创建、管理和部署。通过简单的命令，就可以创建一个新的项目，启动服务，或者进行其他操作。
- 🧈 **Message 对象 / Protobuf 支持**：使用 Protobuf（Protocol Buffers）进行数据的序列化和反序列化。Protobuf 是一种高效的二进制数据编码格式，相比传统的 JSON 或 XML，它具有更小的体积和更快的解析速度，能够显著提高消息在网络传输中的效率，减少带宽的占用。在 LiteBoty 中，通过定义 Protobuf 消息类型（如 ProtoMessage 和 ProtoMetadata），确保了消息在不同服务之间的一致性和可靠性，方便了跨服务的消息传递和处理。

## 入门

### Quick Start

#### 1. 安装 Redis 并配置允许访问
Redis 是 LiteBoty 框架所依赖的关键组件，用于消息的订阅和发布。以下是安装 Redis 并配置允许访问的步骤：

首先，使用以下命令安装 Redis：
```shell
apt install redis-server
```

安装完成后，需要配置 Redis 以允许外部访问（如果需要）。默认情况下，Redis 只允许本地访问。你可以编辑 Redis 配置文件 `/etc/redis/redis.conf`，找到并修改以下配置项：
```plaintext
bind 127.0.0.1 ::1
```
将其改为：
```plaintext
bind 0.0.0.0
```
这样 Redis 就可以接受来自任何 IP 地址的连接。

修改完成后，重启 Redis 服务使配置生效：
```shell
systemctl restart redis-server
```

#### 2. 安装 LiteBoty 框架
LiteBoty 框架可以通过 `pip` 进行安装，使用以下命令：
```shell
pip install liteboty
```

#### 3. 创建项目
使用 LiteBoty 的命令行工具创建一个新的项目。假设项目名称为 `mybot`，可以使用以下命令：
```shell
liteboty create mybot
```
创建完成后，项目目录大概是这样：
```plaintext
.
├── config
│   └── config.json
├── services
│   └── hello.py
```

#### 4. 配置项目
在项目目录下，你会找到一个 `config` 文件夹，其中包含一个 `config.json` 文件。以下是推荐使用的新版本（2.0）配置文件示例：

```json
{
    "version": "2.0",
    "REDIS": {
        "host": "localhost",
        "port": 6379,
        "password": null
    },
    "LOGGING": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - File: %(filename)s - Line: %(lineno)s - %(message)s",
        "log_dir": "logs",
        "max_bytes": 10485760,
        "backup_count": 5
    },
    "SERVICES": {
        ".services.hello.service.HelloService": {
            "enabled": true,
            "priority": 50,
            "config": {
                "welcome_text": "hello liteboty!"
            }
        }
    }
}
```

#### 5. 写第一个服务
在项目中创建第一个服务。当前，项目已经为你生成了一个 `services/hello.py`，将下面的代码覆盖到该文件中：

```python
from liteboty.core import Service


class HelloService(Service):
    def __init__(self, **kwargs):
        super().__init__("HelloService", **kwargs)
        self.add_timer("timer1", interval=0, callback=self.say_somthing, count=1)

    def say_somthing(self):
        self.config.get("welcome_text", "hello...")
```

#### 6. 运行项目
配置完成后，在项目根目录下，使用以下命令运行项目：
```shell
liteboty run --config config/config.json
```
项目启动后，你应该能看到 `"hello liteboty!"` 的输出，这表示你的第一个服务已经成功运行。

### 配置文件格式

LiteBoty 支持两种配置文件格式：新版本（2.0）和旧版本（1.0）。新版本配置格式提供了更多功能，如服务启停控制和启动优先级设置，推荐使用。

#### 新版本配置格式（2.0）

```json
{
    "version": "2.0",
    "REDIS": {
        "host": "localhost",
        "port": 6379,
        "password": null
    },
    "LOGGING": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - File: %(filename)s - Line: %(lineno)s - %(message)s",
        "log_dir": "logs",
        "max_bytes": 10485760,
        "backup_count": 5
    },
    "SERVICES": {
        "liteboty_sg_tts_service.service.TTSService": {
            "enabled": true,
            "priority": 90
        },
        "liteboty_sg_mipicam_capture_service.service.MIPICamCaptureService": {
            "enabled": true,
            "priority": 99,
            "config": {
                "frame_width": 640,
                "frame_height": 480,
                "capture_fps": 15
            }
        },
        "liteboty_sg_segment_service.service.SegService": {
            "enabled": true,
            "priority": 100
        }
    }
}
```

#### 旧版本配置格式（1.0）

```json
{
    "REDIS": {
        "host": "localhost",
        "port": 6379,
        "password": null
    },
    "LOGGING": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - File: %(filename)s - Line: %(lineno)s - %(message)s",
        "log_dir": "logs",
        "max_bytes": 10485760,
        "backup_count": 5
    },
    "SERVICES": [
        ".services.hello.service.HelloService"
    ],
    "SERVICE_CONFIG": {
        "HelloService": {
            "welcome_text": "hello liteboty!"
        }
    },
    "CONFIG_MAP": {
        "HelloService": ".services.hello.service.HelloService"
    }
}
```

#### 配置项详解

##### `version`
- 配置文件版本，用于区分新旧配置格式
- `"2.0"`: 新版本格式（推荐）
- `"1.0"`: 旧版本格式

##### `REDIS`
Redis 连接配置：
- `host`: Redis 服务器主机地址
- `port`: Redis 服务器端口
- `password`: Redis 连接密码（如不需要密码则为 null）
- `db`: Redis 数据库索引
- `socket_timeout`: 连接超时时间
- `socket_connect_timeout`: 连接建立超时时间
- `decode_responses`: 是否自动解码响应

##### `LOGGING`
日志配置：
- `level`: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- `format`: 日志格式
- `log_dir`: 日志文件目录
- `max_bytes`: 单个日志文件最大大小
- `backup_count`: 日志文件备份数量

##### `SERVICES` (新版本格式)
服务配置，每个服务包含以下字段：
- `enabled`: 是否启用该服务（true/false）
- `priority`: 服务启动优先级（数字越小优先级越高）
- `config`: 服务特定配置（可选）

##### `SERVICES` (旧版本格式)
服务路径列表，每个元素是一个服务的导入路径。

##### `SERVICE_CONFIG` (旧版本格式)
服务配置字典，键为服务名称，值为服务特定配置。

##### `CONFIG_MAP` (旧版本格式)
服务名称到服务路径的映射。

### 服务优先级

在新版本配置（2.0）中，你可以通过 `priority` 字段设置服务的启动优先级。数字越小，优先级越高，服务会越早启动。这对于有依赖关系的服务非常有用，例如数据库服务应该在使用数据库的服务之前启动。

默认情况下，所有服务的优先级为 100。如果多个服务具有相同的优先级，它们的启动顺序是不确定的。

示例：
```json
"SERVICES": {
    "liteboty_sg_tts_service.service.TTSService": {
        "enabled": true,
        "priority": 90
    },
    "liteboty_sg_mipicam_capture_service.service.MIPICamCaptureService": {
        "enabled": true,
        "priority": 99
    }
}
```

在这个例子中，`TTSService` 会先于 `MIPICamCaptureService` 启动。

### 服务启停控制

新版本配置（2.0）允许你通过 `enabled` 字段控制服务是否启用。这使得你可以在不修改代码的情况下，通过配置文件启用或禁用特定服务。

```json
"liteboty_sg_segment_service.service.SegService": {
    "enabled": false,
    "priority": 100
}
```

在这个例子中，`SegService` 将不会被加载和启动。

### 配置热重载

LiteBoty 支持配置热重载，当配置文件发生变更时，框架会自动检测并重新加载配置。这包括：

1. 停止已禁用的服务
2. 启动新启用的服务
3. 重启配置发生变更的服务

这使得你可以在不重启整个应用的情况下，动态调整服务的配置和启停状态。

### 服务导入方式

在 LiteBoty 中，SERVICES 配置项用于指定需要加载的服务。它支持两种导入方式：路径导入和 module 导入。

**路径导入**

如果服务的导入路径以 "." 开头，则表示使用路径导入。路径导入适用于项目内部自定义的服务。例如：

```json
".services.hello.service.HelloService": {
    "enabled": true,
    "priority": 50,
    "config": {
        "welcome_text": "hello liteboty!"
    }
}
```

在这个例子中，".services.hello.service.HelloService" 表示从项目内部的相对路径中导入 HelloService 服务。

**module 导入**

如果服务的导入路径不带 "." 开头，则表示使用 module 导入。module 导入适用于通过 pip 安装的第三方服务。例如：

```json
"liteboty_sg_tts_service.service.TTSService": {
    "enabled": true,
    "priority": 90
}
```

在这个例子中，"liteboty_sg_tts_service.service.TTSService" 表示从通过 pip 安装的 liteboty_sg_tts_service 模块中导入 TTSService 服务。