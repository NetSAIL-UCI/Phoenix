# Note you need gnuplot 4.4 for the pdfcairo terminal.
#set terminal pdfcairo font "Helvetica,8" linewidth 4 rounded
# set size ratio 0.75
#set terminal postscript monochrome font "Helvetica, 22" linewidth 4 rounded 
set terminal pdfcairo dashed font "Gill Sans,10" linewidth 2 rounded fontscale 1.0

# Line style for axes
# set style line 80 lt rgb "#808080"

# # Line style for grid
set style line 81 lt 0  # dashed
set style line 81 lt rgb "#808080"  # grey
# set missing "?"

set key inside top right font ",9" # top outside
set key samplen 1.1

set grid back linestyle 81
set border 3 back linestyle 80 # Remove border on top and right.  These
             # borders are useless and make it harder
                          # to see plotted lines near the border.
                              # Also, put it in grey; no need for so much emphasis on a border.
                              set xtics nomirror
                              set ytics nomirror

set output "asplos_25/fig8b.pdf"
set ylabel "Time (in seconds)" font ",10" 
set xlabel "Servers" font ",10" #offset 2

# set style fill solid

set xrange [10:*]
set yrange [0:3599]
set logscale x
set logscale y
# set style data histogram
# set style histogram cluster gap 1
set style fill solid


plot 'asplos_25/processedData/timeplot.txt' using 1:2:xticlabels(1) with linespoints title "PhoenixCost" lc rgb "red" lw 2 lt 2 pointtype 2,\
'' using 1:3 with linespoints title "PhoenixFair" lc rgb "#0000FF" lw 2 lt 3 dashtype "_" pointtype 10,\
'' using 1:4 with linespoints title "Default"  lc rgb "#2ecc71"  lw 2 dashtype "--" pointtype 11,\
# "../processedData/lp_time.txt" using 1:2 title "LPCost" with linespoints lc rgb "#6495ED",\
# "../processedData/lp_time.txt" using 1:3 title "LPFair" with linespoints lc rgb "#E033FF"