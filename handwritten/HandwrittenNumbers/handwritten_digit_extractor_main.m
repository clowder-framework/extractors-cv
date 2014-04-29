global config
global models

%intersect
load('models_intersect')
%linear
% load('models_linear')

cd mnist-sphog;
addpath ..

main

%intersect
config.KERNEL_TYPE = 4;
%linear
% config.KERNEL_TYPE = 0;



