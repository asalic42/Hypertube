FILE='./docker-compose-dev.yml'

all: compose
	docker compose -f ${FILE} up -d --build

compose :
	@if [ ! -f ${FILE} ]; then\
		cp ${FILE}.template ${FILE};\
		sed -i "s|placeholder|${PWD}|g" ${FILE};\
	fi

down:
	docker compose -f ${FILE} down -t 10

re : down all

clean_docker:
	docker stop $$(docker ps -qa);\
	docker rm $$(docker ps -qa);\
	docker rmi -f $$(docker images -qa);\
	docker volume rm $$(docker volume ls -q);\

clean: clean_docker

prune: down clean
	echo "y" | docker system prune -a

.Phony : all down clean re clean_docker prune fclean