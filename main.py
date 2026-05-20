# 这是个0.00版本的仿Claude Code 目的在于学习

import sys
from pathlib import Path
from src.cmdLine.cli import MinClaudeCode

# 获得当前根目录
_src_dir = Path(__file__).resolve().parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


if __name__ == '__main__':
    cli = MinClaudeCode()
    cli.run()
