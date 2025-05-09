import gym
import numpy as np
from dm_control import suite


class DeepMindControl:
    metadata = {}

    def __init__(self, name, action_repeat=1, size=(64, 64), camera=None, seed=0):
        domain, task = name.split("_", 1)
        if domain == "cup":  # Only domain with multiple words.
            domain = "ball_in_cup"
        if isinstance(domain, str):

            self._env = suite.load(
                domain,
                task,
                task_kwargs={"random": seed},
            )
        else:
            assert task is None
            self._env = domain()
        self._action_repeat = action_repeat
        self._size = size
        if camera is None:
            camera = dict(quadruped=2).get(domain, 0)
        self._camera = camera
        self.reward_range = [-np.inf, np.inf]

    @property
    def observation_space(self):
        spaces = {}
        for key, value in self._env.observation_spec().items():
            if len(value.shape) == 0:
                shape = (1,)
            else:
                shape = value.shape
            spaces[key] = gym.spaces.Box(-np.inf, np.inf, shape, dtype=np.float32)
        # Note: Removed the image space definition
        return gym.spaces.Dict(spaces)

    @property
    def action_space(self):
        spec = self._env.action_spec()
        return gym.spaces.Box(spec.minimum, spec.maximum, dtype=np.float32)

    def step(self, action):
        assert np.isfinite(action).all(), action
        reward = 0
        for _ in range(self._action_repeat):
            time_step = self._env.step(action)
            reward += time_step.reward or 0
            if time_step.last():
                break
        # 仅保留特定观察结果
        obs = dict(time_step.observation)
        filtered_obs = {
            k: obs[k] for k in obs if k in ["position", "velocity", "height"]
        }
        filtered_obs["is_terminal"] = (
            False if time_step.first() else time_step.discount == 0
        )
        filtered_obs["is_first"] = time_step.first()
        done = time_step.last()
        info = {"discount": np.array(time_step.discount, np.float32)}
        return filtered_obs, reward, done, info

    def reset(self):
        time_step = self._env.reset()
        obs = dict(time_step.observation)
        filtered_obs = {
            k: obs[k] for k in obs if k in ["position", "velocity", "height"]
        }
        filtered_obs["is_terminal"] = (
            False if time_step.first() else time_step.discount == 0
        )
        filtered_obs["is_first"] = time_step.first()
        return filtered_obs

    def render(self, *args, **kwargs):
        if kwargs.get("mode", "rgb_array") != "rgb_array":
            raise ValueError("Only render mode 'rgb_array' is supported.")
        return self._env.physics.render(*self._size, camera_id=self._camera)

    # Removed the render method since it's no longer needed for physical parameters
    def reset_state(self, new_position, new_velocity):
        self._env.physics.named.data.qpos[:] = new_position
        self._env.physics.named.data.qvel[:] = new_velocity

        # 更新物理模拟状态
        self._env.physics.after_reset()

        # 现在环境状态已更新，渲染图片
        image = self.render(mode="rgb_array")
        return image
