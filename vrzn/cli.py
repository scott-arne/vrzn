import click


@click.command()
@click.option("-n", "--name", default="User", help="More personal address")
def main(name: str):
    print(f'Hello {name}')


# This allows the module to be run with: python -m vrzn.cli
if __name__ == '__main__':
    main()

