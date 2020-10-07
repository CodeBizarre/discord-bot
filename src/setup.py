from setuptools import setup, find_packages

from discordbot.core.discord_bot import VERSION

setup(
    name="discordbot",
    version=VERSION,
    description="An extensible Discord bot using Discord.py's cogs",
    url="https://github.com/CodeBizarre/discord-bot",
    author="CodeBizarre",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3"
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "discord.py[voice]>=1.4<1.5",
        "xkcd>=2.4<2.5",
        "sqlitedict>=1.6.0<1.7",
        "praw>=6.5<6.6",
        "aiohttp[speedups]>=3.6<3.7"
    ],
    entry_points={
        "console_scripts": [
            "discordbot=discordbot.main:main"
        ]
    }
)
