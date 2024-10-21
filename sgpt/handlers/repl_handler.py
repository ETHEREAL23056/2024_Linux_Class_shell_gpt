from typing import Any

import typer
from rich import print as rich_print
from rich.rule import Rule

from ..role import DefaultRoles, SystemRole
from ..utils import run_command
from .chat_handler import ChatHandler
from .default_handler import DefaultHandler


class ReplHandler(ChatHandler):
    def __init__(self, chat_id: str, role: SystemRole, markdown: bool) -> None:
        existing_chats = self.chat_session.list()
        if chat_id == '-ls':
            # 在产生对话之前显示已经存在的对话列表，用户可以选择已经存在的对话也可以新建对话
            if existing_chats:
                typer.echo("Existing Dialogs:")
                for index, chat_id in enumerate(existing_chats):
                    typer.echo(f"{index + 1}. {chat_id.as_posix().split('/')[-1]}")

                # 创建提示信息
                while True:
                    selected_index = typer.prompt("Please select a dialog ID (or input 'n' to create a new dialog)",
                                                  default='n')

                    if selected_index.lower() == 'n':
                        # 要求输入-ls,-sa,-dl以外的非重复名称
                        new_id = typer.prompt(
                            "Please input the name of new chat (default 'default' and '-ls', '-sa' and '-dl' is forbidden)",
                            default='default')
                        if new_id in ('-ls', '-sa', '-dl'):
                            typer.secho("Invalid dialog name, please try again.", fg="red")
                        elif self.chat_session.exists(new_id):
                            typer.secho("Dialog name already exists, please try another", fg="red")
                        else:
                            chat_id = new_id
                            break
                    else:
                        try:
                            selected_index = int(selected_index) - 1
                            if 0 <= selected_index < len(existing_chats):
                                chat_id = existing_chats[selected_index]
                                break
                            else:
                                typer.secho("Invalid dialog ID, please try again.", fg="red")
                        except ValueError:
                            typer.secho("Invalid input, please enter a number or 'n'.", fg="red")
        elif chat_id == '-sa':
            # 输出筛选提示信息
            while True:
                keyword = typer.prompt("Please input keyword for searching (print 'exit' to exit)")
                if keyword.lower() == '':
                    continue
                elif keyword.lower() == 'exit':
                    raise typer.Exit()
                else:
                    # 根据输入的关键词筛选信息-粗粒度检索
                    count = 0
                    for _, chat_id in enumerate(existing_chats):
                        message_list = self.chat_session.get_messages(chat_id)
                        for i in range(len(message_list)):
                            # 仅检索提问的关键词
                            message = message_list[i]
                            if message.startswith("assistant:") or message.startswith("system:"):
                                continue
                            else:
                                content = message[6:]
                                if keyword in content:
                                    count += 1
                                    typer.secho(f"-----dialog{count}-----", fg="red")
                                    self.print_message(message)
                                    self.print_message(message_list[i + 1])
                    if count == 0:
                        typer.secho("No dialog found.", fg="red")
        elif chat_id =='-dl':
            while True:
                existing_chats = self.chat_session.list()
                if existing_chats:
                    typer.echo("Existing Dialogs:")
                    for index, chat_id in enumerate(existing_chats):
                        typer.echo(f"{index + 1}. {chat_id.as_posix().split('/')[-1]}")

                    # 创建提示信息
                    while True:
                        selected_index = typer.prompt("Please select a dialog ID (or input 'e' to exit)")

                        if selected_index.lower() == 'e':
                            raise typer.Exit()
                        elif selected_index.lower() != '':
                            try:
                                selected_index = int(selected_index) - 1
                                if 0 <= selected_index < len(existing_chats):
                                    chat_id = existing_chats[selected_index]
                                    _, res_info = self.chat_session.delete_session(chat_id)
                                    typer.secho(res_info, fg="red")
                                    break
                                else:
                                    typer.secho("Invalid dialog ID, please try again.", fg="red")
                            except ValueError:
                                typer.secho("Invalid input, please enter a number or 'e'.", fg="red")

        super().__init__(chat_id, role, markdown)

    @classmethod
    def _get_multiline_input(cls) -> str:
        multiline_input = ""
        while (user_input := typer.prompt("...", prompt_suffix="")) != '"""':
            multiline_input += user_input + "\n"
        return multiline_input

    def handle(self, init_prompt: str, **kwargs: Any) -> None:  # type: ignore
        if self.initiated:
            rich_print(Rule(title="Chat History", style="bold magenta"))
            self.show_messages(self.chat_id)
            rich_print(Rule(style="bold magenta"))

        # 提示信息
        info_message = (
            "Entering REPL mode, press Ctrl+C to exit."
            if not self.role.name == DefaultRoles.SHELL.value
            else (
                "Entering shell REPL mode, type [e] to execute commands "
                "or [d] to describe the commands, press Ctrl+C to exit."
            )
        )
        typer.secho(info_message, fg="yellow")

        if init_prompt:
            rich_print(Rule(title="Input", style="bold purple"))
            typer.echo(init_prompt)
            rich_print(Rule(style="bold purple"))

        full_completion = ""
        while True:
            # Infinite loop until user exits with Ctrl+C.
            prompt = typer.prompt(">>>", prompt_suffix=" ")
            if prompt == '"""':
                prompt = self._get_multiline_input()
            if prompt == "exit()":
                raise typer.Exit()
            if init_prompt:
                prompt = f"{init_prompt}\n\n\n{prompt}"
                init_prompt = ""
            if self.role.name == DefaultRoles.SHELL.value and prompt == "e":
                typer.echo()
                run_command(full_completion)
                typer.echo()
                rich_print(Rule(style="bold magenta"))
            elif self.role.name == DefaultRoles.SHELL.value and prompt == "d":
                DefaultHandler(
                    DefaultRoles.DESCRIBE_SHELL.get_role(), self.markdown
                ).handle(prompt=full_completion, **kwargs)
            else:
                full_completion = super().handle(prompt=prompt, **kwargs)
