#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.writer import *
print('writer import OK')
from scripts.reviewer import *
print('reviewer import OK')
from scripts.quality_score import *
print('quality import OK')
from scripts.evolution_summary import *
print('evo import OK')
print('ALL imports OK')
