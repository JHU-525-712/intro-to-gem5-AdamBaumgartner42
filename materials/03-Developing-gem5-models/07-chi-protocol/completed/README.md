## Install ALL_CHI
To build CHI, I ran the following commands (from the gem5 directory!!!):

1. scons defconfig build/ALL_CHI build_opts/ALL

2. scons setconfig build/ALL_CHI RUBY_PROTOCOL_CHI=y

3. scons build/ALL_CHI/gem5.opt -j$(nproc)

Now I have ALL_CHI as an option yay!


## Run Command
~/materials/03-Developing-gem5-models/07-chi-protocol/completed# /workspaces/intro-to-gem5-AdamBaumgartner42/gem5/build/ALL_CHI/gem5.opt run-test.py

## Replacement Policies
gem5/src/mem/cache/replacement_policies/ReplacementPolicies.py

Update include for new policy - line 41
Update heirarchy.py - line 68
