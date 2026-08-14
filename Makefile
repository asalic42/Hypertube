FILE := ./docker-compose-dev.yml
CERT_DIR := certs
JWT_DIR := jwt_keys
RM := rm -rf

all: cert jwt compose
	docker compose -f ${FILE} up -d --build 

compose :
	@if [ ! -f "$(FILE)" ]; then \
		cp "$(FILE).template" "$(FILE)"; \
	fi; \
	tmp="$(FILE).tmp"; \
	sed "s|placeholder|$$PWD|g" "$(FILE)" > "$$tmp" && mv "$$tmp" "$(FILE)"

down:
	docker compose -f ${FILE} down -t 10


${JWT_DIR}:
	bash scripts/jwt_keys/set_up.sh

jwt: ${JWT_DIR}

${CERT_DIR}:
	bash scripts/cert/set_up.sh

cert: ${CERT_DIR}

test-users :
	./scripts/test_users.sh

re : down all

clean_docker:
	docker stop $$(docker ps -qa);\
	docker rm $$(docker ps -qa);\
	docker rmi -f $$(docker images -qa);\
	docker volume rm $$(docker volume ls -q);\


clean_certs:
	${RM} ${CERT_DIR}
	${RM} db/certs
	${RM} services/proxy/certs
	${RM} services/users/certs
	${RM} services/auth/certs

clean_jwt:
	${RM} ${JWT_DIR}
	${RM} services/proxy/jwt
	${RM} services/users/jwt
	${RM} services/auth/jwt

clean: down clean_certs clean_docker
	${RM} ${FILE}


prune: down clean
	echo "y" | docker system prune -a

.PHONY : all down clean re clean_docker prune fclean