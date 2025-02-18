# LiteBoty

LiteBoty 是一个轻量级的 Python 机器人框架，专注于构建基于 Redis 的消息驱动服务。

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
在项目目录下，你会找到一个 `config` 文件夹，其中包含一个 `config.json` 文件。这个文件是项目的配置文件，以下为现在要使用的配置文件，在这个步骤中，还不需要关注具体配置是什么意思，只需要复制到你的项目中即可

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

### config.json

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

#### 整体概述
这个 JSON 文件是 LiteBoty 框架的配置文件，包含了多个关键配置项，用于配置 Redis 连接、日志记录、服务列表、服务配置以及服务路径映射等信息。

#### 各配置项详细说明

##### `REDIS`
这部分配置用于设置 Redis 连接的相关信息，具体如下：
- `host`：Redis 服务器的主机地址，这里设置为 `localhost`，表示使用本地的 Redis 服务器。
- `port`：Redis 服务器的端口号，设置为 `6379`，这是 Redis 的默认端口。
- `password`：Redis 服务器的连接密码，设置为 `null` 表示不需要密码进行连接。

##### `LOGGING`
此部分配置用于设置日志记录的相关信息，包括日志级别、日志格式、日志存储目录、日志文件的最大大小和备份数量等：
- `level`：日志级别，设置为 `DEBUG`，表示会记录详细的调试信息。
- `format`：日志的输出格式，包含时间、日志记录器名称、日志级别、文件名、行号和具体的日志信息。
- `log_dir`：日志文件存储的目录，设置为 `logs`，表示日志文件将存储在项目根目录下的 `logs` 文件夹中。
- `max_bytes`：单个日志文件的最大大小，设置为 `10485760` 字节（即 10MB）。
- `backup_count`：日志文件的最大备份数量，设置为 `5`，表示当日志文件达到最大大小时，会自动进行轮转备份，最多保留 5 个备份文件。

##### `SERVICES`
这是一个列表，用于指定需要加载的服务的路径。在这个配置中，只有一个服务路径：
- `".services.hello.service.HelloService"`：表示需要加载的服务是 `HelloService`，其路径为 `.services.hello.service`。

在 LiteBoty 中，SERVICES 配置项用于指定需要加载的服务。它支持两种导入方式：路径导入和 module 导入。

**路径导入**

如果服务的导入路径以 "." 开头，则表示使用路径导入。路径导入适用于项目内部自定义的服务。例如：

```json
"SERVICES": [
    ".services.hello.service.HelloService"
]
```

在这个例子中，".services.hello.service.HelloService" 表示从项目内部的相对路径中导入 HelloService 服务。

**module 导入**

如果服务的导入路径不带 "." 开头，则表示使用 module 导入。module 导入适用于通过 pip 安装的第三方服务。例如：

```json
"SERVICES": [
    "external_service_module.ExternalService"
]
```

在这个例子中，"external_service_module.ExternalService" 表示从通过 pip 安装的 external_service_module 模块中导入 ExternalService 服务。


##### `SERVICE_CONFIG`
这是一个字典，用于为每个服务配置特定的参数。在这个配置中，为 `HelloService` 服务配置了一个参数：
- `"HelloService"`：服务的名称。
  - `"welcome_text"`：服务的配置参数，值为 `"hello liteboty!"`，可以在 `HelloService` 服务中使用这个参数。

##### `CONFIG_MAP`
这是一个字典，用于建立服务名称和服务路径之间的映射关系。在这个配置中，只有一个映射关系：
- `"HelloService"`：服务的名称。
  - `".services.hello.service.HelloService"`：服务的路径。

这个映射关系的作用是在 `watchdog` 监测到配置文件变更时，决定需要重载哪个服务。由于在注册中心 `registry` 中使用服务名称（`Service Name`）作为键来存储服务，而在 `_load_service` 方法中使用的是服务路径（`service path`），所以需要通过这个映射关系来确定服务重载时使用的正确路径。

#### 关于 `CONFIG_MAP` 的设计缺陷说明
当前的 `CONFIG_MAP` 设计是由于前期设计的遗漏产生的一个缺陷。在理想情况下，注册中心和服务加载过程应该使用统一的标识（服务名称或服务路径），避免出现这种需要额外映射的情况。在后续的开发中，会对这部分进行合理化改进，以提高代码的一致性和可维护性。
