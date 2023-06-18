import sys
sys.path.append('../')
import cequalw2 as w2

df1 = w2.read('/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Detroit Reservoir/cwo_11.csv', 2002, ['TDS', 'Gen1', 'ISS1', 'ISS2'])
df2 = w2.read_met('/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Detroit Reservoir/InputFiles/metDetroit2002.csv', 2002)

fig1 = w2.tiny_plot(df1)
fig1.savefig('w2_viewer_single_plot.png')

fig2 = w2.tiny_multi_plot(df2)
fig2.savefig('w2_viewer_multi_plot.png')