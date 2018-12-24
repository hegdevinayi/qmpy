import os
import logging
from django.db import models

import qmpy.materials.element as elt

logger = logging.getLogger(__name__)


class PotentialError(Exception):
    """Base class to handle errors related to pseudopotentials."""
    pass


class Potential(models.Model):
    """
    Class for storing a VASP potential.

    Relationships:
        | :class:`qmpy.Element` via element

    Attributes:
        | date
        | elec_config
        | enmax
        | enmin
        | gw
        | id
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
        ident.append('(v: {})'.format(self.release))
        return ' '.join(ident)

    @classmethod
    def read_potcar(cls, potfile):
        """
        Import pseudopotential(s) from VASP POTCAR and save them to database.

        Arguments:
            potfile:
                String with the path to the POTCAR file.

        Output:
            List of :class:`qmpy.Potential` objects.
        """

        # Read entire POTCAR file
        with open(potfile, 'r') as fr:
            pots = fr.read()

        # If the file VERSION exists in the parent directory, read in the
        # release info (manually added)
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
                        telt = ''.join([e for e in potcar['name'].split('.')[0] if not e.isdigit()])
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

                    if 'GW' in line:
                        potcar['gw'] = True
                    if 'PAW' in line:
                        potcar['paw'] = True
                    if 'US' in line:
                        potcar['us'] = True

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
        | convention
        | element_id
        | id
        | l
        | ligand_id
        | ox
        | u

    """
    element = models.ForeignKey(elt.Element, related_name='hubbards_set')
    ligand = models.ForeignKey(elt.Element, related_name='+', null=True,
                               blank=True)

    convention = models.CharField(max_length=20)
    element_id = models.CharField(max_length=20)
    ligand_id = models.CharField(max_length=20)
    l = models.IntegerField(default=-1)
    ox = models.FloatField(default=None, null=True)
    u = models.FloatField(default=0)

    class Meta:
        app_label = 'qmpy'
        db_table = 'hubbards'

    def __nonzero__(self):
        if self.u > 0 and self.l != -1:
            return True
        else:
            return False

    def __eq__(self, other):
        if self.element != other.element:
            return False
        elif self.ligand != other.ligand:
            return False
        elif self.u != other.u:
            return False
        elif self.l != other.l:
            return False
        return True

    def __str__(self):
        retval = [self.element_id]
        if self.ox:
            retval.append('+{:d}'.format(self.ox))
        if self.ligand:
            retval.append('-{}'.format(self.ligand_id))
        retval.append(' (U={:0.2f}, L={:d})'.format(self.u, self.l))
        return ''.join(retval)

    @property
    def key(self):
        return '{}_{:0.2f}'.format(self.element_id, self.u)

    @classmethod
    def get(cls, element_id, ligand_id=None, ox=None, u=0, l=-1):
        element = elt.Element.objects.get(symbol=element_id)
        ligand = None
        if ligand_id:
            ligand = elt.Element.objects.get(symbol=ligand_id)
        hub, new = Hubbard.objects.get_or_create(
            element_id=element_id, element=element,
            ligand_id=ligand_id, ligand=ligand,
            ox=ox, u=u, l=l)
        if new:
            hub.save()
        return hub
