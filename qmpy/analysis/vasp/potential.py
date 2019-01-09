# -*- coding: utf-8 -*-

import os
import logging

from django.db import models

import qmpy.materials.element as elt
import qmpy.utils as utils

logger = logging.getLogger(__name__)


class PotentialError(Exception):
    """Base class to handle errors related to VASP potentials."""
    pass


class HubbardError(Exception):
    """Base class to handle errors related to Hubbard parameters."""
    pass


class Potential(models.Model):
    """
    Class for storing a VASP potential.

    Relationships:
        | :class:`qmpy.Element` via element

    Attributes:
        | id
        | date
        | elec_config
        | enmax
        | enmin
        | gw
        | name
        | paw
        | potcar
        | release
        | us
        | xc
    """
    element = models.ForeignKey(elt.Element, related_name='potential_set')

    date = models.CharField(max_length=20)
    elec_config = models.TextField(blank=True, null=True)
    enmax = models.FloatField()
    enmin = models.FloatField()
    gw = models.BooleanField(default=False)
    name = models.CharField(max_length=10)
    paw = models.BooleanField(default=False)
    potcar = models.TextField()
    release = models.CharField(max_length=10)
    us = models.BooleanField(default=False)
    xc = models.CharField(max_length=3)

    class Meta:
        app_label = 'qmpy'
        db_table = 'vasp_potentials'

    def __str__(self):
        # E.g. Li_sv PAW PBE GW (v: r5_4_0)
        ident = [self.name]
        if self.paw:
            ident.append('PAW')
        elif self.us:
            ident.append('US')
        ident.append(self.xc)
        if self.gw:
            ident.append('GW')
        if self.release != 'unknown':
            ident.append('{}'.format(self.release))
        return ' '.join(ident)

    @classmethod
    def read_potcar(cls, potfile='POTCAR'):
        """
        Import pseudopotential(s) from VASP POTCAR and save them to database.

        Args:
            potfile:
                String with the path to the POTCAR file.

                Defaults to file "POTCAR" in the current working directory.

        Returns:
            List of :class:`qmpy.Potential` objects.
        """

        # Read entire POTCAR file
        with open(potfile, 'r') as fr:
            pots = fr.read()

        # If the file VERSION exists in the parent directory, read in the
        # release info (note: this file is usually manually added)
        potfile_dir = os.path.dirname(os.path.abspath(potfile))
        version_file = os.path.join(potfile_dir, '..', 'VERSION')
        version = 'unknown'
        if os.path.exists(version_file):
            with open(version_file, 'r') as fr:
                version = fr.readline().strip()

        # Split into the component POTCARs
        pots = pots.strip().split('End of Dataset')

        # Parse each file
        potobjs = []
        for pot in pots:
            if not pot:
                continue

            # Get key information from POTCAR
            potcar = {}
            potcar['release'] = version
            for line in pot.split('\n'):

                if 'TITEL' in line:
                    try:
                        potcar['name'] = line.split()[3]
                    # except for the "H_AE" all-electron? potential
                    except IndexError:
                        potcar['name'] = 'H_AE'
                    # Li_sv, As_sv_GW, Dy_3, etc.
                    if '_' in potcar['name']:
                        telt = potcar['name'].split('_')[0]
                    # H.25, H1.66, etc.
                    elif '.' in potcar['name']:
                        telt = ''.join([e for e in potcar['name'].split('.')[0]
                                        if not e.isdigit()])
                    # Al, Cu, etc. regular ones
                    else:
                        telt = potcar['name']

                    date = line.split()[-1]
                    if potcar['name'] == 'H_AE':
                        date = 'None'
                    potcar['date'] = date

                    if not elt.Element.objects.filter(symbol=telt).exists():
                        err_msg = "Unknown element in potential: {}".format(telt)
                        raise PotentialError(err_msg)
                    potcar['element'] = elt.Element.objects.get(symbol=telt)

                    potcar['gw'] = 'GW' in line
                    potcar['paw'] = 'PAW' in line
                    potcar['us'] = 'US' in line

                if 'ENMAX' in line:
                    data = line.split()
                    potcar['enmax'] = float(data[2].rstrip(';'))
                    potcar['enmin'] = float(data[5])

                if 'VRHFIN' in line:
                    potcar['elec_config'] = line.split(':')[-1].strip()

                if 'LEXCH' in line:
                    key = line.split()[-1]
                    if key == '91':
                        potcar['xc'] = 'GGA'
                    elif key == 'CA':
                        potcar['xc'] = 'LDA'
                    elif key == 'PE':
                        potcar['xc'] = 'PBE'

            potobj, created = cls.objects.get_or_create(**potcar)
            if created:
                potobj.potcar = pot
            potobjs.append(potobj)
        return potobjs


class Hubbard(models.Model):
    """
    Base class for a hubbard correction parameterization.

    Relationships:
        | :class:`qmpy.Element` via element, ligand


    Attributes:
        | id
        | element_id (from relationship)
        | ligand_id (from relationship)
        | convention
        | hubbard_l
        | hubbard_u
        | oxidation_state

    """
    element = models.ForeignKey(elt.Element, related_name='hubbard_set')
    ligand = models.ForeignKey(elt.Element, related_name='+', null=True,
                               blank=True)

    convention = models.CharField(max_length=20)
    hubbard_l = models.IntegerField(default=-1)
    hubbard_u = models.FloatField(default=0)
    oxidation_state = models.FloatField(default=None, null=True)

    class Meta:
        app_label = 'qmpy'
        db_table = 'hubbards'

    def __nonzero__(self):
        if self.hubbard_u > 0 and self.hubbard_l != -1:
            return True
        else:
            return False

    def __eq__(self, other):
        if self.element != other.element:
            return False
        elif self.ligand != other.ligand:
            return False
        elif self.hubbard_l != other.hubbard_l:
            return False
        elif self.hubbard_u != other.hubbard_u:
            return False
        return True

    def __str__(self):
        ident = [self.element_id]
        if self.oxidation_state is not None:
            if utils.is_integer(self.oxidation_state):
                ident.append('{}+'.format(int(self.oxidation_state)))
            else:
                ident.append('{:.1f}+'.format(self.oxidation_state))
        if self.ligand:
            ident.append('-{}'.format(self.ligand_id))
        ident.append(' (U={:0.2f}, L={:d})'.format(self.hubbard_u,
                                                   self.hubbard_l))
        return ''.join(ident)

    @property
    def key(self):
        """String with key for the module-level `qmpy.HUBBARDS` dictionary."""
        return '{}_{:0.2f}'.format(self.element_id, self.hubbard_u)

    @classmethod
    def get(cls,
            element_id,
            ligand_id=None,
            convention=None,
            oxidation_state=None,
            hubbard_u=0,
            hubbard_l=-1):
        """Create a new Hubbard object to store parameters for an element,
        or get an already-created object corresponding to the input
        parameters if it exists.

        Args:
            element_id:
                String with the symbol of the element. (Required.)

            convention:
                String with the name of the parameterization convention.
                E.g. "wang", "aykol", etc.

                Defaults to None.

            ligand_id:
                String with the symbol of the ligand element.

                Defaults to None.

            oxidation_state:
                Float with the oxidation state of the element.

                Defaults to None.

            hubbard_u:
                Float with the Hubbard-U parameter.

                Defaults to U = 0.

            hubbard_l:
                Integer with the l-quantum number for which the Hubbard-U
                parameter is provided.

                Use l = -1 for no onsite interactions as per VASP INCAR, and
                l = {0, 1, 2, 3} for {s, p, d, f}-orbitals.

                Defaults to (LDAUL =) -1.

        Returns:
            `qmpy.Hubbard` object with the Hubbard parameterization.

        """
        hub, new = cls.objects.get_or_create(
            element_id=element_id,
            ligand_id=ligand_id,
            convention=convention,
            oxidation_state=oxidation_state,
            hubbard_l=hubbard_l,
            hubbard_u=hubbard_u
        )
        if new:
            hub.save()
        return hub
