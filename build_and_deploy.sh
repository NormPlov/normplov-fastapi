docker rmi -f fast_api

docker build -t fast_api .

docker run -p 3333:8000 fast_api