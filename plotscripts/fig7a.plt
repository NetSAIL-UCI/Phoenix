    # Note you need gnuplot 4.4 for the pdfcairo terminal.
#set terminal pdfcairo font "Helvetica,8" linewidth 4 rounded
#set size ratio 0.6
#set terminal postscript monochrome font "Helvetica, 22" linewidth 4 rounded 
set terminal pdfcairo dashed font "Gill Sans,10" linewidth 2 rounded fontscale 1.0

# Line style for axes
set style line 80 lt rgb "#808080"

# Line style for grid
set style line 81 lt 0  # dashed
set style line 81 lt rgb "#808080"  # grey
# set missing "?"

set grid back linestyle 81
set border 3 back linestyle 80 # Remove border on top and right.  These
             # borders are useless and make it harder
                          # to see plotted lines near the border.
                              # Also, put it in grey; no need for so much emphasis on a border.
                              set xtics nomirror
                              set ytics nomirror
# reset
# unset key; set xtics nomirror; set ytics nomirror; set border front;
# div=1.1; bw = 0.9; h=1.0; BW=0.9; wd=10;  LIMIT=255-wd; white = 0
#unset key
# set key samplen 1.1
#set key title "Over-allocation factor"
#set key inside top right font ",9" 
#set key above font ",7" horizontal
#set key spacing 0.5 samplen 0.5 height 0.7

set output "asplos_25/fig7a.pdf"
set ylabel "Critical Service Availability" font ",9" 
set xlabel "Cluster Capacity Failed (%)" font ",10" #offset 2

# set key inside bottom left font ",7" # top outside
set key left at graph 0.2, 0.6 font ",7"
set key samplen 1.1 spacing 1.5
# set auto x
# set yrange [0:*]
# set xtics ("10" 0, "20" 1, "30" 2, "40" 3, "50" 4, "60" 5, "70" 6, "80" 7, "90" 8)
set xtics font ",10"
set ytics font ",10" #0,.1,0.5
set style line 1 lt 1 lw 0.5
set yrange[0:1]
# set arrow 1 from 40,0 to 40,100 nohead dt "--" lc rgb "red"

# set xrange [10:90]
# set xtics 0.1, 0.1, 0.9
# set style data histogram
# set style histogram cluster gap 1
# # set style fill solid
# set style line 1 lc rgb '#000000' lw 1
# set style fill pattern 2 border lt 1
# set boxwidth 1

# set boxwidth bw
# set multiplot




plot "asplos_25/processedData/eval_results_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-10000_resilience_score.txt" u (($1*100)):2 title "PhoenixCost" with linespoints lc rgb "#e74c3c" lw 2 lt 2 pointtype 2, \
'' u (($1*100)):3 title "PhoenixFair" with linespoints lc rgb "#3498db" lw 2 lt 3 dashtype "_" pointtype 10, \
 '' u (($1*100)):4 title "Priority" with linespoints lc rgb "#f39c12" lw 2 dashtype "--" pointtype 11, \
  '' u (($1*100)):5 title "Fair" with linespoints lc rgb "#9b59b6" lw 2  dashtype ".." pointtype 6, \
   '' u (($1*100)):6 title "Default" with linespoints lc rgb "#2ecc71" lw 2  dashtype "-." pointtype 8, \
#    '' u (($1*100)):7 title "PriorityDG" with linespoints lc rgb "#f39c12" lw 2 dashtype "--" pointtype 11, \
#   '' u (($1*100)):8 title "FairNonDG" with linespoints lc rgb "#9b59b6" lw 2  dashtype ".." pointtype 6, \
# unset border; set xtics format " "; set ytics format " "; set ylabel " "
# call 'hist_r.gnu'
# unset multiplot