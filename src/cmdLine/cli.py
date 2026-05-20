from datetime import datetime
from src.cmdLine import cli_print
from src.llm.agent import *


class MinClaudeCode:
    def __init__(self):
        self.agent_loop = AgentLoop()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def handle_cmd(self, command: str) -> bool:
        cmd= command.strip().lower()

        if cmd in ["/q", "/quit", "/exit"]:
            cli_print.print_info("Goodbye! Thanks for using MinClaudeCode CLI.")
            return False

        if cmd in ["/clear"]:
            cli_print.clear_screen()
            cli_print.print_header(self.session_id)
            cli_print.print_info("Conversation cleared!")
            return True

        elif cmd == '/help':
            cli_print.print_welcome()
            return True

        elif cmd == '/tokens':
            req_tokens, rsp_tokens = self.agent_loop.get_tokens()
            cli_print.show_token_count(req_tokens, rsp_tokens)
            return True

        elif cmd.startswith('/'):
            cli_print.print_unknown_cmd(command)
            return True

        return True

    # Agent主流程
    def run(self):
        cli_print.clear_screen()
        cli_print.print_welcome()
        while True:
            message = cli_print.get_input()
            if not message:
                continue

            if message.startswith("/"):
               if not self.handle_cmd(message):
                   break
               continue

            cli_print.print_user_input(message)

            # 与LLM交互主流程
            self.agent_loop.run(
                message,
                cli_print.show_status,
                cli_print.print_info,
                cli_print.typewriter_then_markdown,
                cli_print.print_tool_call,
                cli_print.print_tool_result)

            cli_print.print_blank()


