# -*- coding: utf-8 -*-

import os
import time
import torch
from torchvision import transforms
from model import DenseNet
from data_loader import customData


class AverageMeter(object):
    """
    Computes and stores the average and current value
    Copied from: https://github.com/pytorch/examples/blob/master/imagenet/main.py
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def train_epoch(model, loader, optimizer, epoch, n_epochs, print_freq=1):
    batch_time = AverageMeter()
    losses = AverageMeter()
    error = AverageMeter()

    # Model on train mode
    model.train()

    end = time.time()
    for batch_idx, (input, target) in enumerate(loader):
        # Create vaiables
        if torch.cuda.is_available():
            input_var = torch.autograd.Variable(input.cuda(async=True))
            target_var = torch.autograd.Variable(target.cuda(async=True))
        else:
            input_var = torch.autograd.Variable(input)
            target_var = torch.autograd.Variable(target)

        # compute output
        output = model(input_var)
        loss = torch.nn.functional.cross_entropy(output, target_var)

        # measure accuracy and record loss
        batch_size = target.size(0)
        _, pred = output.data.cpu().topk(1, dim=1)
        error.update(torch.ne(pred.squeeze(), target.cpu()).float().sum() / batch_size, batch_size)
        losses.update(loss.item(), batch_size)

        # compute gradient and do SGD step
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        # print stats
        if batch_idx % print_freq == 0:
            res = '\t'.join([
                'Epoch: [%d/%d]' % (epoch + 1, n_epochs),
                'Iter: [%d/%d]' % (batch_idx + 1, len(loader)),
                'Time %.3f (%.3f)' % (batch_time.val, batch_time.avg),
                'Loss %.4f (%.4f)' % (losses.val, losses.avg),
                'Error %.4f (%.4f)' % (error.val, error.avg),
            ])
            print(res)

    # Return summary statistics
    return batch_time.avg, losses.avg, error.avg


def test_epoch(model, loader, print_freq=1, is_test=True):
    batch_time = AverageMeter()
    losses = AverageMeter()
    error = AverageMeter()

    # Model on eval mode
    model.eval()

    end = time.time()
    print(len(loader))
    for batch_idx, (input, target) in enumerate(loader):
        # Create vaiables
        if torch.cuda.is_available():
            input_var = torch.autograd.Variable(input.cuda(async=True), volatile=True)
            target_var = torch.autograd.Variable(target.cuda(async=True), volatile=True)
        else:
            input_var = torch.autograd.Variable(input, volatile=True)
            target_var = torch.autograd.Variable(target, volatile=True)

        # compute output
        output = model(input_var)
        loss = torch.nn.functional.cross_entropy(output, target_var)

        # measure accuracy and record loss
        batch_size = target.size(0)
        _, pred = output.data.cpu().topk(1, dim=1)
        error.update(torch.ne(pred.squeeze(), target.cpu()).float().sum() / batch_size, batch_size)
        losses.update(loss.data[0], batch_size)

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        # print stats
        if batch_idx % print_freq == 0:
            res = '\t'.join([
                'Test' if is_test else 'Valid',
                'Iter: [%d/%d]' % (batch_idx + 1, len(loader)),
                'Time %.3f (%.3f)' % (batch_time.val, batch_time.avg),
                'Loss %.4f (%.4f)' % (losses.val, losses.avg),
                'Error %.4f (%.4f)' % (error.val, error.avg),
            ])
            print(res)

    # Return summary statistics
    return batch_time.avg, losses.avg, error.avg


def train(model, train_set, save, n_epochs=100, valid_size=420,
          batch_size=30, lr=0.1, wd=0.0001, momentum=0.9, seed=None):
    if seed is not None:
        torch.manual_seed(seed)

    # Create train/valid split
    if valid_size:
        indices = torch.randperm(len(train_set))
        train_indices = indices[:len(indices) - valid_size]
        train_sampler = torch.utils.data.sampler.SubsetRandomSampler(train_indices)
        valid_indices = indices[len(indices) - valid_size:]
        valid_sampler = torch.utils.data.sampler.SubsetRandomSampler(valid_indices)

    # Data loaders
    if valid_size:
        train_loader = torch.utils.data.DataLoader(train_set, batch_size=batch_size, sampler=train_sampler,
                                                   pin_memory=(torch.cuda.is_available()), num_workers=0)
        valid_loader = torch.utils.data.DataLoader(train_set, batch_size=batch_size, sampler=valid_sampler,
                                                   pin_memory=(torch.cuda.is_available()), num_workers=0)
    else:
        train_loader = torch.utils.data.DataLoader(train_set, batch_size=batch_size, shuffle=True,
                                                   pin_memory=(torch.cuda.is_available()), num_workers=0)
        valid_loader = None

    # Model on cuda
    if torch.cuda.is_available():
        model = model.cuda()

    # Wrap model for multi-GPUs, if necessary
    model_wrapper = model
    if torch.cuda.is_available() and torch.cuda.device_count() > 1:
        model_wrapper = torch.nn.DataParallel(model).cuda()

    # Optimizer
    optimizer = torch.optim.SGD(model_wrapper.parameters(), lr=lr, momentum=momentum, nesterov=True, weight_decay=wd)
    scheduler = torch.optim.lr_scheduler.MultiStepLR(optimizer, milestones=[0.5 * n_epochs, 0.75 * n_epochs],
                                                     gamma=0.1)

    # Start log
    with open(os.path.join(save, 'results.csv'), 'w') as f:
        f.write('epoch,train_loss,train_error,valid_loss,valid_error,test_error\n')

    # Train model
    best_error = 1
    for epoch in range(n_epochs):
        scheduler.step()
        _, train_loss, train_error = train_epoch(
            model=model_wrapper,
            loader=train_loader,
            optimizer=optimizer,
            epoch=epoch,
            n_epochs=n_epochs,
        )
        _, valid_loss, valid_error = test_epoch(
            model=model_wrapper,
            loader=valid_loader,
            is_test=(not valid_loader)
        )

        # Determine if model is the best
        if valid_loader and valid_error < best_error:
            best_error = valid_error
            print('New best error: %.4f' % best_error)
            torch.save(model.state_dict(), os.path.join(save, 'model_para.pkl'))
        else:
            torch.save(model.state_dict(), os.path.join(save, 'model_para.pkl'))

        # Log results
        with open(os.path.join(save, 'results.csv'), 'a') as f:
            f.write('%03d,%0.6f,%0.6f,%0.5f,%0.5f,\n' % (
                (epoch + 1),
                train_loss,
                train_error,
                valid_loss,
                valid_error,
            ))

    # Final test of model on test set有测试集时输出test_error
#    model.load_state_dict(torch.load(os.path.join(save, 'model.dat')))
#    if torch.cuda.is_available() and torch.cuda.device_count() > 1:
#        model = torch.nn.DataParallel(model).cuda()
#    test_results = test_epoch(
#        model=model,
#        loader=test_loader,
#        is_test=True
#    )
#    _, _, test_error = test_results
#    with open(os.path.join(save, 'results.csv'), 'a') as f:
#        f.write(',,,,,%0.5f\n' % (test_error))
#    print('Final test error: %.4f' % test_error)


def demo(save, depth=100, growth_rate=32, efficient=False, valid_size=420,
         n_epochs=50, batch_size=30, seed=None):
    """
    A demo to show off training of efficient DenseNets.
    Trains and evaluates a DenseNet-BC on 铝型材（自制数据集接口）.

    Args:
        data (str) - path to directory where data should be loaded from/downloaded
            (default $DATA_DIR)
        save (str) - path to save the model to (default /tmp)

        depth (int) - depth of the network (number of convolution layers) (default 40)
        growth_rate (int) - number of features added per DenseNet layer (default 12)
        efficient (bool) - use the memory efficient implementation? (default True)

        valid_size (int) - size of validation set
        n_epochs (int) - number of epochs for training (default 300)
        batch_size (int) - size of minibatch (default 256)
        seed (int) - manually set the random seed (default None)
    """

    # Get densenet configuration
    if (depth - 4) % 3:
        raise Exception('Invalid depth')
    block_config = [(depth - 4) // 6 for _ in range(3)]

    # Data transforms
    mean = [0.5071, 0.4867, 0.4408]
    stdv = [0.2675, 0.2565, 0.2761]
    train_transforms = {'train':transforms.Compose([
        transforms.RandomCrop(224, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=stdv)
    ])}


    # Datasets
    train_set = {'train':customData(txt_path=('train.txt'),
                           data_transforms=train_transforms,
                           dataset='train')}

    # Models
    model = DenseNet(
        growth_rate=growth_rate,
        block_config=block_config,
        num_classes=12,
        small_inputs=False,
        efficient=efficient 
        )
    print(model)

    # Make save directory
    if not os.path.exists(save):
        os.makedirs(save)
    if not os.path.isdir(save):
        raise Exception('%s is not a dir' % save)

    # Train the model
    train(model=model, train_set=train_set['train'], save=save,
          valid_size=valid_size, n_epochs=n_epochs, batch_size=batch_size, seed=seed)
    print('Done!')


"""
A demo to show off training of efficient DenseNets.
Trains and evaluates a DenseNet-BC on CIFAR-10.

Try out the efficient DenseNet implementation:
python demo.py --efficient True --data <path_to_data_dir> --save <path_to_save_dir>

Try out the naive DenseNet implementation:
python demo.py --efficient False --data <path_to_data_dir> --save <path_to_save_dir>

Other args:
    --depth (int) - depth of the network (number of convolution layers) (default 40)
    --growth_rate (int) - number of features added per DenseNet layer (default 12)
    --n_epochs (int) - number of epochs for training (default 300)
    --batch_size (int) - size of minibatch (default 256)
    --seed (int) - manually set the random seed (default None)
"""
if __name__ == '__main__':
    demo(save='./logs_densenet')
