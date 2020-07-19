
VERILOGS = \
src/audio_info_frame.sv \
src/audio_clock_regeneration_packet.sv \
src/audio_sample_packet.sv \
src/auxiliary_video_information_info_frame.sv \
src/hdmi.sv \
src/packet_assembler.sv \
src/packet_picker.sv \
src/source_product_description_info_frame.sv \
src/tmds_channel.sv

VERILOGS += verilator/testbench.sv

VERILATOR=verilator
CCO=-fno-var-tracking-assignments
SPEED='OPT_FAST="-O2"'
CPUS=2

all:
        # -Wall
	$(VERILATOR) -DVERILATOR=1 -Wno-fatal --cc --trace $(VERILOGS) --top-module testbench --l2-name v --exe verilator/sim_main.cpp
	$(MAKE) -C obj_dir OPT_FAST="-O2" -f Vtestbench.mk Vtestbench
