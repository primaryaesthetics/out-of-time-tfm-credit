# 2015H1-E: the published protocol beside this one

In time: the 20,000-row test cell of each of 5 fold(s); out of time: the mean over the build's scored cohorts. Each entry is the mean over folds and context seeds, with the spread across them in brackets where it exceeds the fourth decimal.

| auc | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.6853 [0.6721, 0.6925] | 0.7006 [0.6941, 0.7106] | 0.6861 [0.6711, 0.7004] |
| out of time, vintage cohorts | 0.7002 | 0.7101 | 0.7037 [0.7010, 0.7053] |

| gini | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.3707 [0.3442, 0.3851] | 0.4013 [0.3882, 0.4212] | 0.3723 [0.3422, 0.4009] |
| out of time, vintage cohorts | 0.4004 | 0.4201 | 0.4073 [0.4020, 0.4105] |

| ks | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.2888 [0.2666, 0.3014] | 0.3132 [0.2996, 0.3201] | 0.2864 [0.2633, 0.3163] |
| out of time, vintage cohorts | 0.3070 | 0.3150 | 0.3074 [0.3056, 0.3107] |

| average_precision | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0508 [0.0472, 0.0560] | 0.0552 [0.0484, 0.0659] | 0.0500 [0.0451, 0.0585] |
| out of time, vintage cohorts | 0.0682 | 0.0753 | 0.0705 [0.0692, 0.0714] |

| brier | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0228 [0.0215, 0.0236] | 0.0227 [0.0215, 0.0235] | 0.0228 [0.0215, 0.0236] |
| out of time, vintage cohorts | 0.0299 | 0.0298 | 0.0299 [0.0298, 0.0299] |

| log_loss | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.1066 [0.1016, 0.1097] | 0.1057 [0.1015, 0.1087] | 0.1066 [0.1018, 0.1100] |
| out of time, vintage cohorts | 0.1335 | 0.1319 | 0.1331 [0.1325, 0.1335] |

| accuracy | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.8839 [0.8544, 0.9059] | 0.9134 [0.8727, 0.9380] | 0.9024 [0.8762, 0.9358] |
| out of time, vintage cohorts | 0.9065 [0.8841, 0.9217] | 0.9174 [0.8823, 0.9348] | 0.9133 [0.8781, 0.9552] |

| balanced_accuracy | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.5743 [0.5624, 0.5844] | 0.5706 [0.5480, 0.6103] | 0.5679 [0.5443, 0.5924] |
| out of time, vintage cohorts | 0.5685 [0.5575, 0.5832] | 0.5663 [0.5521, 0.5919] | 0.5649 [0.5233, 0.5944] |

| f1 | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0928 [0.0844, 0.1039] | 0.1028 [0.0852, 0.1199] | 0.0947 [0.0781, 0.1149] |
| out of time, vintage cohorts | 0.1210 [0.1181, 0.1233] | 0.1253 [0.1203, 0.1297] | 0.1189 [0.0798, 0.1296] |

| precision | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0573 [0.0510, 0.0666] | 0.0702 [0.0536, 0.0868] | 0.0616 [0.0484, 0.0792] |
| out of time, vintage cohorts | 0.0871 [0.0810, 0.0916] | 0.0969 [0.0845, 0.1039] | 0.0918 [0.0828, 0.1117] |

| recall | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.2495 [0.2112, 0.2887] | 0.2108 [0.1391, 0.3347] | 0.2167 [0.1327, 0.2939] |
| out of time, vintage cohorts | 0.2079 [0.1689, 0.2622] | 0.1918 [0.1438, 0.2822] | 0.1933 [0.0627, 0.2917] |

| mcc | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0745 [0.0646, 0.0867] | 0.0830 [0.0652, 0.1039] | 0.0744 [0.0567, 0.0940] |
| out of time, vintage cohorts | 0.0903 [0.0856, 0.0958] | 0.0951 [0.0888, 0.1044] | 0.0897 [0.0616, 0.1051] |

| observed_over_expected | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 1.0128 [0.9556, 1.0501] | 1.0141 [0.9529, 1.0541] | 1.0138 [0.9495, 1.0645] |
| out of time, vintage cohorts | 1.4950 | 1.4279 | 1.4620 [1.4173, 1.4848] |

| abs_log_oe | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0365 [0.0157, 0.0489] | 0.0379 [0.0132, 0.0527] | 0.0331 [0.0013, 0.0625] |
| out of time, vintage cohorts | 0.3980 | 0.3526 | 0.3756 [0.3446, 0.3913] |

| cox_slope | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.9675 [0.8997, 1.0218] | 0.9706 [0.8856, 1.0511] | 1.0187 [0.7864, 1.2433] |
| out of time, vintage cohorts | 1.0642 | 1.0059 | 1.1011 [1.0103, 1.1703] |

| brier_miscalibration | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0001 | 0.0001 [0.0001, 0.0001] | 0.0001 [0.0000, 0.0001] |
| out of time, vintage cohorts | 0.0003 | 0.0002 | 0.0003 |

| psi | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0003 [0.0001, 0.0005] | 0.0004 [0.0002, 0.0007] | 0.0005 [0.0001, 0.0011] |
| out of time, vintage cohorts | 0.0328 | 0.0174 | 0.0177 [0.0164, 0.0203] |

| predicted_positive_share | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.1044 [0.0810, 0.1353] | 0.0730 [0.0454, 0.1194] | 0.0842 [0.0461, 0.1137] |
| out of time, vintage cohorts | 0.0752 [0.0575, 0.1009] | 0.0633 [0.0429, 0.1041] | 0.0675 [0.0175, 0.1088] |

| threshold | scorecard | gbm | gbm-50k |
|---|---|---|---|
| in time, random fold | 0.0446 [0.0399, 0.0482] | 0.0531 [0.0433, 0.0590] | 0.0479 [0.0405, 0.0620] |
| out of time, vintage cohorts | 0.0446 [0.0399, 0.0482] | 0.0531 [0.0433, 0.0590] | 0.0479 [0.0405, 0.0620] |

Ranking on auc (high is better):
- in time, random fold: gbm (0.7006) > gbm-50k (0.6861) > scorecard (0.6853)
- out of time, vintage cohorts: gbm (0.7101) > gbm-50k (0.7037) > scorecard (0.7002)

Ranking on brier (low is better):
- in time, random fold: gbm (0.0227) > scorecard (0.0228) > gbm-50k (0.0228)
- out of time, vintage cohorts: gbm (0.0298) > gbm-50k (0.0299) > scorecard (0.0299)

Ranking on log_loss (low is better):
- in time, random fold: gbm (0.1057) > scorecard (0.1066) > gbm-50k (0.1066)
- out of time, vintage cohorts: gbm (0.1319) > gbm-50k (0.1331) > scorecard (0.1335)

Ranking on abs_log_oe (low is better):
- in time, random fold: gbm-50k (0.0331) > scorecard (0.0365) > gbm (0.0379)
- out of time, vintage cohorts: gbm (0.3526) > gbm-50k (0.3756) > scorecard (0.3980)

Ranking on f1 (high is better):
- in time, random fold: gbm (0.1028) > gbm-50k (0.0947) > scorecard (0.0928)
- out of time, vintage cohorts: gbm (0.1253) > scorecard (0.1210) > gbm-50k (0.1189)
