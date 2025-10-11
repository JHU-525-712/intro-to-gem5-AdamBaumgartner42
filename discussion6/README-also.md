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

4. cd ~/gem5

5. install VEGA_x86
docker run --volume $(pwd):$(pwd) -w $(pwd) ghcr.io/gem5/gcn-gpu:v24-0 \
 bash -c "PYTHON_CONFIG=$(which python3-config) scons build/VEGA_X86/gem5.opt -j$(nproc)"

--- What happens here? ---
This should install VEGA_x86
Do you see ~/gem5/build/VEGA_X86/gem5.opt?

6. cd ~/
go back to the base directory

7.
docker run --volume $(pwd):$(pwd) -w $(pwd) ghcr.io/gem5/gcn-gpu:v24-0 \
  bash -c "gem5/build/VEGA_X86/gem5.opt gem5/configs/example/apu_se.py -n 3 --gfx-version=gfx902 -c discussion6/bin/square"

--- What happens here? ---
Run the simulation with with the program square.
Results added to ~/m5out/stats.txt







