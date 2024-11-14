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
set key inside top right font ",9" # top outside
set key samplen 1.1

set output "asplos_25/fig8c.pdf"
set ylabel "Cluster Capacity Normalized" font ",9" 
set xlabel "Cluster Capacity Failed (%)" font ",10" #offset 2

# set style fill solid
set auto x
# set xrange [0 :*]
set yrange [0:*]
set xtics ("0" 0,"10" 1, "20" 2, "30" 3, "40" 4, "50" 5, "60" 6, "70" 7, "80" 8, "90" 9)

set style data histogram
set style histogram cluster gap 1
# set style fill solid

set boxwidth 0.95 relative

plot 'asplos_25/processedData/packing_efficiency.txt' using 2 title "PhoenixPlanner" lc rgb "#3498db" fillstyle pattern 3,\
'' using 3 title "PhoenixScheduler" lc rgb "#e74c3c" fillstyle pattern 1,\
'' using 4 title "DefaultScheduler" lc rgb "#2ecc71" fillstyle pattern 2
# '' using 5 title "LP" lc rgb "#6495ED"
# plot the data
# plot '../processedData/alibaba-scatter_plot.txt' using 1:2 notitle with points lc rgb "#40E0D0" pointtype 3 pointsize 1.5,\
# plot '../processedData/alibaba-cdf-app1.txt' using 1:2 notitle with linespoints pointtype 4 pointsize 1.5,\
# '../processedData/alibaba-cdf-app2.txt' using 1:2 notitle with linespoints lc rgb "#6495ED" pointtype 10 pointsize 1.5,\
# '../processedData/alibaba-cdf-app3.txt' using 1:2 notitle with linespoints lc rgb "#FFBF00" pointtype 6 pointsize 1.5,\
# '../processedData/alibaba-cdf-app4.txt' using 1:2 notitle with linespoints lc rgb "red"  pointtype 2 pointsize 1.5
# In case need a title
# '../processedData/alibaba-scatter_plot-app4.txt' using 1:2 with points pointtype 7 pointsize 1 title 'Data Points'

# lc rgb "#40E0D0" lw 2  dashtype ".." pointtype 6
# lc rgb "#6495ED" lw 2 dashtype "--" pointtype 4
# lc rgb "#FFBF00" lw 2 lt 3 dashtype "_" pointtype 10
# lc rgb "red" lw 2 lt 2 pointtype 2