set -e

tput clear
make
obj_dir/Vtestbench
time python tv.py log
qiv out.png
# ~/local/bin/iverilog -g2005-sv $SRC
