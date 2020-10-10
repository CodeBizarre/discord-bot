ifeq ($(OS),Windows_NT)
	SHELL = CMD
	CLEARS = cls
	RM = rmdir /s /q
	CP = xcopy /E /I /Y

	CREATE = if not exist env ( python -m venv env )
	ACTIVATE = env\Scripts\activate
	FixPath = $(subst /,\,$1)
	ZIP = pwsh -Command "Compress-Archive * discord-bot-win64.zip"
else
	CLEARS = clear
	RM = rm -rf
	CP = cp -r

	CREATE = if [ ! -d "env" ]; then python3 -m venv env; fi
	ACTIVATE = . env/bin/activate
	FixPath = $1
	ZIP = tar -zcf discord-bot-linux64.zip *
endif

PYTHON_VERSION_MIN=3.7
PYTHON_VERSION=$(shell python3 -c 'import sys; print("%d.%d"% sys.version_info[0:2])' )
PYTHON_VERSION_OK=$(shell python3 -c 'import sys;\
  print(int(float("%d.%d"% sys.version_info[0:2]) >= $(PYTHON_VERSION_MIN)))' )

ifeq ($(PYTHON_VERSION_OK),0)
  $(error "Need python $(PYTHON_VERSION) >= $(PYTHON_VERSION_MIN)")
endif

help:
	echo "Usage: make <dev | package | package-dev | clean | clear-package>"

clear-package:
	-$(RM) $(call FixPath,discordbot/dist)
	-$(CLEARS)

clean:
	-deactivate
	-$(RM) $(call FixPath,env)
	-$(RM) $(call FixPath,discordbot/build)
	-$(RM) $(call FixPath,discordbot/dist)
	-$(CLEARS)

env:
	$(CREATE)

dev: env
	$(ACTIVATE) && pip install --ignore-installed --no-cache-dir -r requirements.txt && pip install -e .

pyinstaller: env
	$(ACTIVATE) && pip install --ignore-installed --no-cache-dir pyinstaller==4.0

package: clear-package dev pyinstaller
	$(ACTIVATE) && cd discordbot && pyinstaller --onefile discord-bot.spec
	$(CP) $(call FixPath,discordbot/plugins discordbot/dist/plugins)
	$(CP) $(call FixPath,discordbot/config discordbot/dist/config)
	cd $(call FixPath,discordbot/dist) && $(ZIP)

install: help ;
