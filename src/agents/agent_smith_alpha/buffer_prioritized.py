import random
import torch
import numpy as np
from collections import deque


class SumTree:
  """
  Sum Tree data structure.

  A Sum Tree is a Binary Tree data structure where each parent node has a
  maximum of 2 child nodes. In Sum Trees the value of a parent node is equal to
  the sum of the values of its children.
  """

  write = 0

  def __init__(self, capacity):
    self.capacity = capacity
    self.tree = np.zeros(2 * capacity - 1)
    self.data = np.zeros(capacity, dtype=object)

  def _propagate(self, idx, change):
    parent = (idx - 1) // 2

    self.tree[parent] += change

    if parent != 0:
      self._propagate(parent, change)

  def _retrieve(self, idx, s):
    left = 2 * idx + 1
    right = left + 1

    if left >= len(self.tree):
      return idx

    if s <= self.tree[left]:
      return self._retrieve(left, s)
    else:
      return self._retrieve(right, s - self.tree[left])

  def total(self):
    return self.tree[0]

  def add(self, p, data):
    idx = self.write + self.capacity - 1

    self.data[self.write] = data
    self.update(idx, p)

    self.write += 1
    if self.write >= self.capacity:
      self.write = 0

  def update(self, idx, p):
    change = p - self.tree[idx]

    self.tree[idx] = p
    self._propagate(idx, change)

  def get(self, s):
    idx = self._retrieve(0, s)
    dataIdx = idx - self.capacity + 1

    return idx, self.tree[idx], self.data[dataIdx]


class PrioritizedBuffer:

  def __init__(self, max_size, device, alpha=0.6, beta=0.4):
    self.device = device
    self.sum_tree = SumTree(max_size)
    self.alpha = alpha
    self.beta = beta
    self.current_length = 0

  def push(self, state, action, reward, next_state, done):
    priority = 1.0 if self.current_length is 0 else self.sum_tree.tree.max()
    self.current_length = self.current_length + 1
    # priority = td_error ** self.alpha
    experience = (state, action, np.array([reward]), next_state, done)
    self.sum_tree.add(priority, experience)

  def sample(self, batch_size):
    batch_idx, batch, IS_weights = [], [], []
    segment = self.sum_tree.total() / batch_size
    p_sum = self.sum_tree.tree[0]

    for i in range(batch_size):
      a = segment * i
      b = segment * (i + 1)
      s = random.uniform(a, b)
      idx, p, data = self.sum_tree.get(s)
      batch_idx.append(idx)
      batch.append(data)
      prob = p / p_sum
      IS_weight = (self.sum_tree.total() * prob) ** (-self.beta)
      IS_weights.append(IS_weight)

    batch = np.asarray(batch)
    states = np.vstack(batch[:, 0])
    actions = np.vstack(batch[:, 1])
    rewards = np.vstack(batch[:, 2])
    next_states = np.vstack(batch[:, 3])
    dones = np.vstack(batch[:, 4])
    states = torch.from_numpy(states).float().to(device=self.device)
    actions = torch.from_numpy(actions).long().to(device=self.device)
    rewards = torch.from_numpy(rewards).float().to(device=self.device)
    next_states = torch.from_numpy(next_states).float().to(device=self.device)
    dones = torch.from_numpy(dones.astype(np.uint8)).float().to(
      device=self.device)
    return states, actions, rewards, next_states, dones
   # return (states, actions, rewards, next_states, dones), batch_idx, IS_weights

    # state_batch = []
    # action_batch = []
    # reward_batch = []
    # next_state_batch = []
    # done_batch = []

    # for transition in batch:
    #   state, action, reward, next_state, done = transition
    #   state_batch.append(state)
    #   action_batch.append(action)
    #   reward_batch.append(reward)
    #   next_state_batch.append(next_state)
    #   done_batch.append(done)

    # return (state_batch, action_batch, reward_batch, next_state_batch,
    #         done_batch), batch_idx, IS_weights

  def update_priority(self, idx, td_error):
    priority = td_error ** self.alpha
    self.sum_tree.update(idx, priority)

  def __len__(self):
    return self.current_length
