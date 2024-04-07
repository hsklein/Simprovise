g++ -IC:\\boost_1_59_0 -o genmtstates genmtstates.cpp
genmtstates 10000 "rng_states.data"
python savestates_as_npy.py 100 100 "rng_states.data" "mt19937_states.npy"
