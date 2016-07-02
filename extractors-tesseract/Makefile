name = $(shell basename `pwd`)
repo = ncsa
localhost = $(shell ip -4 addr show eth0 | grep -Po 'inet \K[\d.]+')

container: Dockerfile *.sh
	docker build --pull -t $(name) .

push: container
	docker tag -f $(name) $(repo)/$(name)
	docker push $(repo)/$(name):latest

run:
	docker run -t -i -e "RABBITMQ_URI=amqp://guest:guest@$(localhost)/%2f" $(name)

shell:
	docker run -t -i -e "RABBITMQ_URI=amqp://guest:guest@$(localhost)/%2f" $(name) /bin/bash
