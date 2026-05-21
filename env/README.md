# 本地环境目录

这个目录专门存放项目环境相关文件。

## 包含内容

1. `conda-environment.yml`
   用于一键创建 Conda 环境。

## 推荐使用方式

创建环境：

```bash
conda env create -f env/conda-environment.yml
conda activate chinese-chess-agent
```

如果你已经创建过环境，想更新依赖：

```bash
conda env update -f env/conda-environment.yml --prune
conda activate chinese-chess-agent
```

## 百炼配置

项目运行时实际读取的是根目录下的 `config.yaml`。

创建方式：

```bash
cp config.example.yaml config.yaml
```

然后填写你自己的阿里云百炼 API Key。

## Web 运行方式

环境准备好后，项目通过本地 Web 服务运行：

```bash
python main.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```
