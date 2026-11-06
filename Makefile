FILE := ./docker-compose-dev.yml
CERT_DIR := certs
JWT_DIR := jwt_keys
RM := rm -rf
TEST_SERVICES := auth users movies frontend

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

check-launching:
	@set -eu; \
	running_services="$$(docker compose -f "$(FILE)" ps --status running --services)"; \
	missing_services=""; \
	for service in $(TEST_SERVICES); do \
		if ! printf '%s\n' "$$running_services" | grep -Fxq "$$service"; then \
			missing_services="$$missing_services $$service"; \
		fi; \
	done; \
	if [ -n "$$missing_services" ]; then \
		echo "Les conteneurs suivants ne sont pas lances:$$missing_services" >&2; \
		echo "Lancez-les avant les tests avec 'make'." >&2; \
		exit 1; \
	fi

${JWT_DIR}:
	bash scripts/jwt_keys/set_up.sh

jwt: ${JWT_DIR}

${CERT_DIR}:
	bash scripts/cert/set_up.sh

cert: ${CERT_DIR}

re : down all

check-running: check-launching
	@echo "Services en cours d'exécution : $(TEST_SERVICES)"

test: check-running test-auth test-users test-movies test-frontend

test-auth:
	docker compose -f ${FILE} exec -T auth python3 manage.py test auth_app --settings=auth.settings_test

test-users:
	docker compose -f ${FILE} exec -T users python3 manage.py test users_app --settings=users.settings_test

test-movies:
	docker compose -f ${FILE} exec -T movies python3 manage.py test movies_app --settings=movies.settings_test

test-frontend:
	docker compose -f ${FILE} exec -T frontend npm run build

lint:
	docker compose -f ${FILE} exec -T frontend npm run lint

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

.PHONY : all down clean re clean_docker prune fclean check-launching check-running \
         test test-auth test-users test-movies test-frontend lint