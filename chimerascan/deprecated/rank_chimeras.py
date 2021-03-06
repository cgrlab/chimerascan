'''
Created on Feb 5, 2011

@author: mkiyer

Copyright (C) 2011 Matthew Iyer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import logging
import operator
import numpy as np

# local imports
from chimerascan.lib.stats import scoreatpercentile
from merge_spanning_alignments import SpanningChimera

PERMISCUITY_THRESHOLD = 0.01

def get_spanning_read_score(c, anchor_min=10):
    junc_pos = c.junc_pos
    score = 0
    for r in c.spanning_reads:
        anchor = min(junc_pos - r.pos, r.aend - junc_pos)        
        if anchor < anchor_min:
            continue
#        score += max(0, anchor) / float(r.mappings)
        score += 1.0 / r.mappings
    return score

def get_junction_pileup(c):
    arr = np.zeros(c.junc_pos, dtype=np.float)
    for r in c.spanning_reads:
        end = min(c.junc_pos, r.aend)
        arr[r.pos:end] += (1.0 / r.mappings) 
    return arr

def get_anchor_hist(c):
    a, r = divmod(c.junc_pos, 2)
    arr = np.zeros(a + r + 1, dtype=np.float)
    for r in c.spanning_reads:        
        anchor = min(c.junc_pos - r.pos, r.aend - c.junc_pos)
        if anchor >= arr.shape[0]:
            logging.warning("Anchor length %d longer than expected (%d)" % 
                            (anchor, arr.shape[0]))
            anchor = arr.shape[0] - 1
        arr[anchor] += (1.0 / r.mappings)        
    return arr

def get_ranking_props(c):
    return (c.weighted_cov,
            c.encomp_and_spanning,
            get_spanning_read_score(c))
            #int(min(c.mate5p.frac, c.mate3p.frac) > PERMISCUITY_THRESHOLD))

def hist_interp_prob(H, E, X):
    right_inds = []
    left_inds = []
    frac_inds = []
    for d,edges in enumerate(E):        
        # find correct bin
        right_ind = np.searchsorted(edges, X[d], side="left")
        # handle min/max bins
        if right_ind == 0:
            right_ind = 1
        elif right_ind == len(edges):
            right_ind = len(edges) - 1
        right_inds.append(right_ind)
        left_ind = right_ind - 1
        left_inds.append(left_ind)
        # find the fraction between indexes
        left_edge = edges[left_ind]
        right_edge = edges[right_ind]
        if right_edge == 0:
            frac = 0
        else:
            frac = (X[d] - left_edge) / (right_edge - left_edge)
        frac_inds.append(frac)        
        #print 'DIM', d, 'LEFT', edges[left_ind], 'RIGHT', edges[right_ind]
    # add the initial sum first
    right_index = []
    left_index = []
    left_total_indexes = []
    right_total_indexes = []
    for d in xrange(len(E)):
        right_index.append(np.s_[:right_inds[d]])        
        left_index.append(np.s_[:left_inds[d]])
        # find total area bound by this dimension
        lidx = [np.s_[:] for x in xrange(len(E))]
        ridx = [np.s_[:] for x in xrange(len(E))]
        for i in xrange(len(right_inds)):
            ri = right_inds[i]
            li = left_inds[i]
            if i == d:
                continue
            lidx[i] = np.s_[li:]
            ridx[i] = np.s_[ri:]
        left_total_indexes.append(lidx)
        right_total_indexes.append(ridx)
    right_val = np.sum(H[right_index])
    left_val = np.sum(H[left_index])
    #frac = np.max(frac_inds)
    frac = np.mean(frac_inds)
    # compute val
    interp_val = left_val + frac * (right_val - left_val)
    #interp_val = right_val    
    # compute total bound by indexes
    left_total = 0
    right_total = 0
    for d in xrange(len(right_total_indexes)):
        lidx = left_total_indexes[d]
        ridx = right_total_indexes[d]
        left_total += np.sum(H[lidx])
        right_total += np.sum(H[ridx])
        #print d, lidx, ridx, left_total, right_total
    interp_total = left_total + (1.0 - frac) * (right_total - left_total)
    # interp_total = right_total    
    #print 'rt', right_total
    #print 'lt', left_total
    #print 't', interp_total    
    #print 'v', interp_val
    return interp_val / (interp_val + interp_total)

def get_quantiles(a, probs):
    sorted_a = np.sort(a)    
    unique_a = np.unique(a)
    maxbins = probs.shape[0]
    if unique_a.shape[0] <= maxbins:
        edges = list(unique_a)
    else:
        edges = []
        for p in probs:
            score = scoreatpercentile(sorted_a, p)
            if len(edges) > 0 and (score == edges[-1]):
                continue
            edges.append(score)
    if len(edges) == 1:
        return 1
    return edges

def rank_chimeras(input_file, output_file, empirical_prob):
    '''
    rank the chimeras according to the empirical distribution
    of encompassing read coverage, spanning read coverage, 
    and junction permiscuity
    '''
    # profile the chimeras
    arr = []
    for c in SpanningChimera.parse(open(input_file)):        
        arr.append(get_ranking_props(c))
    arr = np.array(arr)
    # choose bin sizes
    maxbins = 500
    bins = []
    for d in xrange(arr.shape[1]):    
        bins.append(get_quantiles(arr[:,d], np.linspace(0, 1, maxbins))) 
    H, edges = np.histogramdd(arr, bins=bins)
    #N = np.sum(H)
    # now rank each chimera using the empirical distribution
    chimera_scores = []
    for c in SpanningChimera.parse(open(input_file)):
        props = get_ranking_props(c)
        p = hist_interp_prob(H, edges, props)
        chimera_scores.append((1-p, c))
    outfh = open(output_file, "w")
    sorted_chimera_scores = sorted(chimera_scores, key=operator.itemgetter(0))
    empirical_probs = np.array([x[0] for x in sorted_chimera_scores])
    prob_cutoff = scoreatpercentile(empirical_probs, empirical_prob)
    
    print >>outfh, '\t'.join(['#gene5p', 'start5p', 'end5p', 'gene3p', 
                              'start3p', 'end3p', 'name', 'weighted_cov', 
                              'strand5p', 'strand3p', 'type', 'distance', 
                              'encompassing_reads', 'encompassing_reads_plus',
                              'encompassing_reads_minus', 'multimap_hist',
                              'isize5p', 'isize3p', 'exons5p', 'exons3p',
                              'junction_permiscuity5p', 
                              'junction_permiscuity3p',
                              'encompassing_ids', 'encompassing_read1',
                              'encompassing_read2', 'junction_id', 
                              'junction_pos', 'homology5p', 'homology3p', 
                              'spanning_reads', 'encomp_and_spanning',
                              'total_reads', 'spanning_info', 
                              'breakpoint_hist', 'empirical_prob']) 
    for p,c in sorted_chimera_scores:
        if p > prob_cutoff:
            break
        arr = get_anchor_hist(c)
        arrstring = ','.join([str(round(x,1)) for x in arr])
        print >>outfh, '\t'.join(map(str, c.to_list() + [arrstring, p]))
    outfh.close() 


def main():
    from optparse import OptionParser
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    parser = OptionParser("usage: %prog [options] <sortedchimeras.bedpe> <chimeras.txt>")
    parser.add_option("--empirical-prob", type="float", metavar="p", 
                      dest="empirical_prob", default=1.0, 
                      help="empirical probability threshold "
                      " for outputting chimeras [default=%default]")
    options, args = parser.parse_args()
    input_file = args[0]
    output_file = args[1]
    rank_chimeras(input_file, output_file, options.empirical_prob)

if __name__ == "__main__":
    main()
    
#def scoreatpercentile(a, p):
#    from math import floor, ceil
#    floatind = (len(a)-1) * p
#    lowind = int(floor(floatind))
#    highind = int(ceil(floatind))
#    # interpolate
#    val = (1 - (floatind - lowind))*a[lowind] + (1 - (highind - floatind))*a[highind]
#    return val

#def test_hist():
#    import scipy.stats
#    
#    x = scipy.stats.norm.rvs(size=100)
#    y = scipy.stats.norm.rvs(size=100)
#    z = scipy.stats.norm.rvs(size=100)
#    arr = np.array([x,y,z])
#    arr = arr.transpose()
#    # choose bin sizes
#    maxbins = 10
#    bins = []
#    for d in xrange(arr.shape[1]):    
#        bins.append(get_quantiles(arr[:,d], np.linspace(0, 1, maxbins))) 
#    #print arr.shape
#    #print bins
#    H, edges = np.histogramdd(arr, bins=bins)
#    N = np.sum(H)
#    for x in np.linspace(-3,3,10):
#        p = hist_interp_prob2(H, edges, (x, 0, 0))        
#        print "X", x, "P", p
#    #print edges 
#
# DEPRECATED: old implementation
#
#def hist_interp_prob(H, E, X):
#    lo_slices = []
#    hi_slices = []
#    fracs = []
#    for d,edges in enumerate(E):        
#        # find bins
#        right_ind = np.searchsorted(edges, X[d], side="left")
#        if right_ind == len(edges):
#            right_ind = len(edges) - 1
#        left_ind = right_ind - 1
#        
#        print 'IND', d, "LEFT", left_ind, "RIGHT", right_ind
#        
#        if right_ind == 0:
#            lo_slices.append(slice(0, 0))        
#            hi_slices.append(slice(0, 1))
#            left_edge = 0        
#        else:
#            # add all histogram counts up to lo_ind
#            lo_slices.append(slice(0, left_ind+1))        
#            hi_slices.append(slice(0, right_ind+1))
#            left_edge = edges[left_ind]
#        # find the fraction between lo_ind and hi_ind
#        right_edge = edges[right_ind]
#        if right_edge == 0:
#            frac = 0
#        else:
#            frac = (X[d] - left_edge) / (right_edge - left_edge)
#        fracs.append(frac)
#    # add the initial sum first
#    lowval = np.sum(H[lo_slices])
#    hival = np.sum(H[hi_slices])
#    avgfrac = np.mean(fracs)
#    val = lowval + avgfrac * (hival - lowval)
#    return val