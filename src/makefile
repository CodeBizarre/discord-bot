ifeq ($(OS),Windows_NT)
	SHELL = CMD
	CLEARS = cls
	RM = rmdir /s /q

	CREATE = if not exist env ( pyython -m venv env )
	ACTIVATE = env\Scripts\activate
	FixPath = $(subst /,\,$1)
else
	CLEARS = clear
	RM = rm -rf

	CREATE = if [ ! -d "env" ]; then python3 -m venv env; fi
	ACTIVATE = . env/bin/activate
	FixPath = $1
endif

PYTHON_VERSION_MIN=3.8
PYTHON_VERSION=$(shell python3 -c 'import sys; print("%d.%d"% sys.version_info[0:2])' )
PYTHON_VERSION_OK=$(shell python3 -c 'import sys;\
  print(int(float("%d.%d"% sys.version_info[0:2]) >= $(PYTHON_VERSION_MIN)))' )

ifeq ($(PYTHON_VERSION_OK),0)
  $(error "Need python $(PYTHON_VERSION) >= $(PYTHON_VERSION_MIN)")
endif

help:
	echo "Usage: make <dev | package | package-dev | clean>"

env:
	$(CREATE)

pyinstaller: env
	$(ACTIVATE) && pip install pyinstaller

dev: env
	$(ACTIVATE) && pip install -r requirements.txt && pip install -e .

package: dev pyinstaller
	$(ACTIVATE) && cd discordbot && pyinstaller --onefile discord-bot.spec

install: help ;

clean:
	-deactivate
	-$(RM) $(call FixPath,env)
	-$(RM) $(call FixPath,discordbot/build)
	-$(RM) $(call FixPath,discordbot/dist)
	-$(CLEARS)
