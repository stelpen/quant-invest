"""Application entry point — starts the Uvicorn ASGI server."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="QuantInvest 量化投资平台")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址 (默认 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="端口 (默认 8000)")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("错误: 未安装 uvicorn, 请运行 pip install -r requirements.txt")
        sys.exit(1)

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
