# transfer weights from grouped convolution implementation to singledecoder implementation
import os
import torch
import sys
root = "/ws/ifp-10_3/hasegawa/junzhez2/Baseline_Model"
sys.path.append(root)
from src.model_multidecoder import Dual_RNN_model
import importlib
from configs.config4 import *
fill_zeros = True
old_path = 'pretrained/raymond_pretrained.pth'
new_path = 'pretrained/raymond_pretrained_newversion.pth'

old_pkg = torch.load(os.path.join(root, old_path))
old_lr = old_pkg['optim_dict']['param_groups'][0]['lr']
model = Dual_RNN_model(enc, bottleneck, hidden, kernel_size=kernel_size, rnn_type=rnn_type, norm=norm, dropout=dropout, bidirectional=True, num_layers=num_layers, K=K, num_spks=num_spks, multiloss=multiloss, mulcat=(mul, cat))

encoder_params = {'params': model.encoder.parameters(), 'lr': old_lr}
separation_params = {'params': model.separation.parameters(), 'lr': old_lr}
decoder_params = {'params': model.decoder.decoders.parameters(), 'lr': old_lr * 4}
vad_params = {'params': model.decoder.vad.parameters(), 'lr': old_lr}
optimizer = torch.optim.Adam([encoder_params, separation_params, decoder_params, vad_params], lr=old_lr, weight_decay=l2)
optim_state = optimizer.state_dict()
for param_group in optimizer.state_dict()['param_groups']:
    param_group['lr'] = param_group['lr'] * 0.94
optimizer.load_state_dict(optim_state)
print('Learning rate adjusted to: %s' % str(optim_state))

print(len(list(model.parameters())), \
    len(list(model.encoder.parameters())) + len(list(model.separation.parameters())) + \
    len(list(model.decoder.decoders.parameters())) + len(list(model.decoder.vad.parameters())))

old_dict = old_pkg['state_dict']
new_dict = model.state_dict()
check_mapping = {}
for key in new_dict.keys():
    check_mapping[key] = 1

for name, param in old_dict.items():
    # print(name)
    if name not in new_dict:
        name = name[len("decoder"):]
        # print(name, param.shape)
        '''
        if not name.startswith(".prelu"):
            if name.startswith('.end'):
                chunks = param.view(-1, 4, *param.size()[1:]).transpose(0, 1)
            else:
                chunks = param.view(4, -1, *param.size()[1:])
        for i in range(4):
            mapped_name = "decoder.decoders." + str(i) + name
            check_mapping[mapped_name] = 1
            mapped_tensor = new_dict[mapped_name]
            if name.startswith('.conv2d'):
                shape_tmp = mapped_tensor.size()
                channels = mapped_tensor.size(0)
                chunk_tmp = chunks[i][:channels, ...]
                assert mapped_tensor.size() == chunk_tmp.size()
                new_dict[mapped_name] = chunk_tmp
            elif name.startswith(".prelu"):
                new_dict[mapped_name] = param
            else:
                assert chunks[i].shape == new_dict[mapped_name].shape
                new_dict[mapped_name] = chunks[i]
        '''
        # print("I'm not sure how to fix this... or if it can be fixed at all.")
    else:
        new_dict[name] = param
        check_mapping[name] = 1

for value in check_mapping.values():
    assert value == 1

# inversely check all names are mapped to
for name, param in new_dict.items():
    # print(name)
    if name not in old_dict:
        name = name.replace("decoder.decoders.", "")[1:]
        assert "decoder" + name in old_dict, "decoder" + name


model.load_state_dict(new_dict)
package = model.serialize(model,
                        optimizer, old_pkg["epoch"],
                        tr_loss=old_pkg["tr_loss"],
                        cv_loss=old_pkg["cv_loss"],
                        val_no_impv=old_pkg["val_no_impv"],
                        random_state=old_pkg["random_state"])
torch.save(package, os.path.join(root, new_path))