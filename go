set -e

PATH=$HOME/local/bin:$PATH
tput clear
make -f verilator/verilator.Makefile
exit
obj_dir/Vtestbench
time python tv.py log
qiv out.png
# ~/local/bin/iverilog -g2005-sv $SRC
