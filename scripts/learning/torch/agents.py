import os
import numpy as np
import torch as T
import torch.nn as nn
import torch.optim as optim
from torch.distributions.categorical import Categorical
from memory import PPOMemory
from networks import ActorNetwork, CriticNetwork


# Gamma is from paper, alpha is learning rate, also from paper

# The rest seems to be the hyperparameter
# N is horizon: number of steps we take before updating

class Agent:
    def __init__(self, n_actions, input_dims, gamma=0.99, alpha=0.0003, gae_lambda=0.95,
            policy_clip=0.2, batch_size=64, N=2048, n_epochs=10, ):
        self.gamma = gamma
        self.policy_clip = policy_clip
        self.n_epochs = n_epochs
        self.gae_lambda = gae_lambda
        
        self.actor = ActorNetwork(n_actions, input_dims, alpha)
        self.critic = CriticNetwork(input_dims, alpha)
        self.memory = PPOMemory(batch_size)

    def remember(self, state, action, probs, vals, reward, done, truncated):
        self.memory.store_memory(state, action, probs, vals, reward, done, truncated)

    def save_models(self):
        print('...saving models...')    
        self.actor.save_checkpoint()
        self.critic.save_checkpoint()

    def load_models(self):
        print('...loading models...')
        self.actor.load_checkpoint()
        self.critic.load_checkpoint()

    def choose_action(self, observation):
        # print([observation])
        state = T.tensor([observation], dtype=T.float).to(self.actor.device)

        dist = self.actor(state)    
        value= self.critic(state)
        action = dist.sample()

        probs = T.squeeze(dist.log_prob(action)).item()
        action = T.squeeze(action).item()
        value = T.squeeze(value).item()

        return action,probs,value

    def learn(self):
        for _ in range(self.n_epochs):
            # print(self.memory.generate_batches())
            state_arr, action_arr, old_probs_arr, vals_arr,\
            reward_arr, dones_arr, truncated, batches =\
                    self.memory.generate_batches()

            values = vals_arr
            advantage = np.zeros(len(reward_arr),dtype=np.float32)

            for t in range(len(reward_arr)-1):
                discount = 1
                # a_t is the advantage each time t, i.e. the goodness of each state
                a_t = 0
                for k in range(t, len(reward_arr)-1):
                    # small_delta t function
                    # print(f"dones: {dones_arr}")
                    a_t += discount*(reward_arr[k] + self.gamma*values[k+1]*\
                            (1-int(dones_arr[k])) - values[k])
                    # gamma * big_lambda
                    discount *= self.gamma*self.gae_lambda
                advantage[t] = a_t
            advantage = T.tensor(advantage).to(self.actor.device)

            values = T.tensor(values).to(self.actor.device)
            for batch in batches:
                states = T.tensor(state_arr[batch],dtype=T.float).to(self.actor.device)
                old_probs = T.tensor(old_probs_arr[batch]).to(self.actor.device) 
                actions = T.tensor(action_arr[batch]).to(self.actor.device) 

                dist = self.actor(states)
                critic_value = self.critic(states)

                critic_value = T.squeeze(critic_value)

                new_probs = dist.log_prob(actions)
                prob_ratio = new_probs.exp() / old_probs.exp()                
                #prob_ratio = (new_probs - old_probs).exp()
                weighted_probs = advantage[batch] * prob_ratio
                weighted_clipped_probs = T.clamp(prob_ratio, 1-self.policy_clip, 
                                        1+self.policy_clip)* advantage[batch]
                actor_loss = -T.min(weighted_probs, weighted_clipped_probs).mean()
                
                returns = advantage[batch] + values[batch]
                critic_loss = (returns-critic_value) ** 2
                critic_loss = critic_loss.mean()

                total_loss = actor_loss + 0.5*critic_loss
                self.actor.optimizer.zero_grad()
                self.critic.optimizer.zero_grad()
                total_loss.backward()
                self.actor.optimizer.step()
                self.critic.optimizer.step()

        self.memory.clear_memory()

























