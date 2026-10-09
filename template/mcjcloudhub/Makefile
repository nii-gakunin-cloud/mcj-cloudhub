stack = ${1:-mcj-cloudhub}
envfile = ./.env
moodle_profile = moodle

include $(envfile)
export


devsetup:
		mkdir -p mcj-data && sudo bash localsetup.sh && cp .env.sample .env
devup:
		docker compose -f docker-compose.yml --env-file $(envfile) --profile $(moodle_profile) up -d
devdown:
		docker compose -f docker-compose.yml --env-file $(envfile) --profile $(moodle_profile) down
devdestroy:
		docker compose -f docker-compose.yml --env-file $(envfile) --profile $(moodle_profile) down -v
devrestart:
		docker compose -f docker-compose.yml --env-file $(envfile) --profile $(moodle_profile) down && \
		docker compose -f docker-compose.yml --env-file $(envfile) --profile $(moodle_profile) up -d
devrestartjh:
		docker compose -f docker-compose.yml --env-file $(envfile) --profile $(moodle_profile) down jupyterhub && \
		docker compose -f docker-compose.yml --env-file $(envfile) --profile $(moodle_profile) up -d jupyterhub

up:
		docker stack deploy -c docker-stack.yml $(stack)
down:
		docker stack rm $(stack)
config:
		docker compose -f docker-stack.yml config