FILE := ./docker-compose-dev.yml
CERT_DIR := certs
RM := rm -rf

all: cert compose
	docker compose -f ${FILE} up -d --build 

compose :
	@if [ ! -f "$(FILE)" ]; then \
		cp "$(FILE).template" "$(FILE)"; \
	fi; \
	tmp="$(FILE).tmp"; \
	sed "s|placeholder|$$PWD|g" "$(FILE)" > "$$tmp" && mv "$$tmp" "$(FILE)"

down:
	docker compose -f ${FILE} down -t 10

${CERT_DIR}:
	bash scripts/cert/set_up.sh

cert: ${CERT_DIR}

re : down all

clean_docker:
	docker stop $$(docker ps -qa);\
	docker rm $$(docker ps -qa);\
	docker rmi -f $$(docker images -qa);\
	docker volume rm $$(docker volume ls -q);\


clean_certs:
	${RM} certs
	${RM} db/certs
	${RM} services/proxy/certs
	${RM} services/users/certs
	${RM} services/auth/certs


clean: clean_certs clean_docker

prune: down clean
	echo "y" | docker system prune -a

.PHONY : all down clean re clean_docker prune fclean