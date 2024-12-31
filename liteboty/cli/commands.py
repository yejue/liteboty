import json
import click
import shutil
from pathlib import Path


@click.group()
def cli():
    """LiteBoty CLI"""
    pass


@cli.command()
@click.argument('name')
def create(name):
    """创建新的LiteBot项目"""
    template_dir = Path(__file__).parent / "templates"
    target_dir = Path(name)

    if target_dir.exists():
        click.echo(f"Directory {name} already exists")
        return

    # 复制项目模板
    shutil.copytree(template_dir / "project", target_dir)

    # 添加 HelloService 到默认 config.json
    with open(target_dir / "config/config.json", "r") as f:
        config = json.load(f)

    config["SERVICES"].append(f".services.hello.service.HelloService")

    click.echo(f"Created project {name}")

    # 写回配置文件
    with open(target_dir / "config/config.json", 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)


@cli.command()
@click.argument('name')
def create_service(name):
    """创建新服务"""
    template_dir = Path(__file__).parent / "templates"
    service_dir = name

    if service_dir.exists():
        click.echo(f"Service {name} already exists")
        return

    # 复制服务模板
    shutil.copytree(template_dir / "service", service_dir)
    click.echo(f"Created service {name}")
