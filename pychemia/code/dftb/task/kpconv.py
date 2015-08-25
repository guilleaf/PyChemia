__author__ = 'Guillermo Avendano-Franco'

import os
import time
import json
import numpy as np
from .._dftb import DFTBplus, read_detailed_out
from pychemia.dft import KPoints
from pychemia import pcm_log


class KPointConvergence:

    def __init__(self, structure, workdir='.', slater_path='.', waiting=False, energy_tolerance=1E-3,
                 output_file='results.json'):

        self.structure = structure
        self.workdir = workdir
        self.slater_path = slater_path
        self.waiting = waiting
        self.energy_tolerance = energy_tolerance
        if isinstance(slater_path, basestring):
            self.slater_path = [slater_path]
        self.results = []
        self.output_file = output_file

    def run(self):

        n = 10
        dftb = DFTBplus()
        kpoints = KPoints()
        kpoints.set_optimized_grid(self.structure.lattice, density_of_kpoints=1000, force_odd=True)
        dftb.initialize(workdir=self.workdir, structure=self.structure, kpoints=kpoints)
        dftb.set_slater_koster(search_paths=self.slater_path)
        grid = None
        energies = []

        while True:
            density = n**3
            kpoints.set_optimized_grid(self.structure.lattice, density_of_kpoints=density, force_odd=True)
            if np.sum(grid) != np.sum(kpoints.grid):
                pcm_log.debug('Trial density: %d  Grid: %s' % (density, kpoints.grid))
                grid = kpoints.grid
                dftb.kpoints = kpoints

                dftb.basic_input()
                dftb.hamiltonian['MaxSCCIterations'] = 50
                if os.path.isfile('charges.bin'):
                    dftb.hamiltonian['ReadInitialCharges'] = True
                dftb.hamiltonian['Mixer'] = {'name': 'DIIS'}
                dftb.set_static()
                dftb.set_inputs()
                dftb.run()
                if self.waiting:
                    dftb.runner.wait()
                while True:
                    if dftb.runner is not None and dftb.runner.poll() is not None:
                        pcm_log.info('Execution completed. Return code %d' % dftb.runner.returncode)
                        filename = dftb.workdir + os.sep + 'detailed.out'
                        ret = read_detailed_out(filename)
                        print 'KPoint_grid= %15s  iSCC= %4d  Total_energy= %10.4f  SCC_error= %9.3E' % (grid,
                                                                                    ret['SCC']['iSCC'],
                                                                                    ret['total_energy'],
                                                                                    ret['SCC']['SCC_error'])
                        n += 2
                        energies.append(ret['total_energy'])
                        break
                    time.sleep(10)
            else:
                n += 2

            self.results.append({'kp_grid': grid,
                                 'iSCC': ret['SCC']['iSCC'],
                                 'Total_energy': ret['total_energy'],
                                 'SCC_error': ret['SCC']['SCC_error']})

            if len(energies) > 2 and abs(max(energies[-3:])-min(energies[-3:])) < self.energy_tolerance:
                break

    def save_json(self):

        wf = open(self.output_file,'w')
        json.dump(self.results, wf)
        wf.close()
