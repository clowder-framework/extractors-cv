function [label, score]=handwritten_digit_classify(filename)
    global config
    global models
    
    im = imread(filename);
    if(length(size(im))==3)
       im = rgb2gray(im); 
    end
    
    im = imresize(im, [28 28]);
    im_row = reshape(im, 1, 28*28);
    norm_type=config.NORM_TYPE;
    im_norm = normalize_data(im_row, norm_type);
   
    blocks = config.BLOCKS;
    H = config.PATCH_H;
    W = config.PATCH_W;
   
    [gw, gh, level_weights] = get_sampling_grid(W,H,blocks,config.DO_OVERLAP);

    param.nori=config.NORI;
    param.ww = W;
    param.hh = H;
   
    dim = 0;
    for i = 1:length(gw),
        dim = dim + (size(gw{i},1)-1)*(size(gw{i},2)-1)*param.nori;
    end
   
    im_features = make_sphog_features(im_norm,param,gw,gh,level_weights);
    
%     load('models_intersect')
    model = cell(1);
    probs = zeros(1, 10);

    tic
    for i=0:9
        model{1} = models{i+1};
        probs(i+1) = predict_single_label(model,[i],im_features);
    end
    
    [score, label] = max(probs);
    label = label-1;
    
end

function f=make_sphog_features(x,param,gw,gh,level_weights)
   I  = reshape(x,param.ww,param.hh);
   f = compute_features(I,param,gw,gh,1,level_weights);
end
