import typer

from services.greeter_service import greet


def main(name: str) -> None:
    print(greet(name))


if __name__ == "__main__":
    typer.run(main)
