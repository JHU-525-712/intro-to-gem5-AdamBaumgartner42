Here are steps to run square.cpp

1. Configure first docker image
docker pull ghcr.io/gem5/gcn-gpu:v24-0

2. Navigate to square.cpp's folder
cd ~/disscussion6/

3. Run make
docker run --rm -v ${PWD}:${PWD} -w ${PWD} ghcr.io/gem5/gcn-gpu:v24-0 make

--- What happens here? ---
Answer: bin/square created
This is the c code I want to use to simulate

