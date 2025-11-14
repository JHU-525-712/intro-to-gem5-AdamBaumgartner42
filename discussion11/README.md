
### Terminal Location
/intro-to-gem5-AdamBaumgartner42#

# my_pthread_program
## Build
gcc -static -pthread -o programs/my_pthread_program programs/my_pthread_program.c
## Run
gem5/build/ALL_MyMSI/gem5.opt gem5/configs/learning_gem5/part3/simple_ruby.py --cmd=~./programs/my_pthread_program

