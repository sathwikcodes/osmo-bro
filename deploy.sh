#!/bin/bash

docker build . --push -t # -t [space] docker-image-name
docker compose up -d --remove-orphans --force-recreate