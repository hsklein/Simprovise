// genmtstates.cpp
//
// Generates state vectors (each containing 624 unsigned ints) for MT19937
// (Mersenne Twister) random number generator substreams.  
//
// This is accomplished by initializing a Boost mt19937 generator instance and 
// then repeatedly jumping ahead in that generator's stream by a specified 
// amount (substream size = 2^50).  At each jump, we write the generator state 
// to an output file in binary format.  
//
// The jumps are performed via the generator's discard() method.  The Boost
// Mersenne Twister implementation uses the fast jump ahead algorithm published
// by Haramoto, Matsumoto and L'Ecuyer (see mersenne_twister.hpp for details)
// for large jumps, making the discard(2^50) call practicable.
//
// Usage: genmtstates <nstreams> <output filename>
//
// Copyright Howard Klein 2015

#include <iostream>
#include <sstream>
#include <fstream>
#include <boost/random/mersenne_twister.hpp>
#include <time.h>
#include <math.h>

const unsigned STATE_SZ = 624;

using namespace std;

int main(int argc, char** argv)
{
    unsigned long long substream_sz = pow(2,50);
    //unsigned NSTREAMS = 1000;

    if (argc != 3) {
        cerr << "usage: " << argv[0] << " <nstreams> <output filename>" 
             << endl;
        exit(1);
    }
    int nstreams = atoi(argv[1]);
    const char* outfilename = argv[2];

    cout << "Generating mt19937 states for " << nstreams
         << " substreams, each of length: " << substream_sz << endl;

    boost::random::mt19937 rng(1962);
    ofstream fout(outfilename, ios::out|ios::binary);
    clock_t startTm = clock();

    for (int i = 0; i < nstreams; ++i) {
        rng.discard(substream_sz);
        std::stringstream input;
        input << rng;
 
        std::vector<unsigned> state;
        unsigned p;
        while (input >> p) {
            state.push_back(p);
        }
        if (state.size() != STATE_SZ) {
            cerr << "State Size Error:" << state.size() << endl;
            exit(1);
        }
        //cout << i << ": " << state[0] << ", " << state[623] << endl;

        fout.write(reinterpret_cast<const char*>(&state[0]), state.size() * sizeof(unsigned));
    }
    clock_t cpuTm = clock() - startTm;
    cout << "nstreams:" << nstreams <<
             ", total cpu:" << cpuTm/CLOCKS_PER_SEC << endl;
}