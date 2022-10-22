# Copyright 2022 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for tfx.dsl.input_resolution.ops.latest_pipeline_run_op."""

import tensorflow as tf
from tfx.dsl.input_resolution import resolver_op
from tfx.dsl.input_resolution.ops import ops
from tfx.orchestration.portable.input_resolution import exceptions
from tfx.utils import test_case_utils
from ml_metadata.proto import metadata_store_pb2


class LatestPipelineRunTest(tf.test.TestCase, test_case_utils.MlmdMixins):

  def setUp(self):
    super().setUp()
    self.init_mlmd()

  def testLatestPipelineRun_Empty(self):
    with self.mlmd_handle as mlmd_handle:
      context = resolver_op.Context(store=mlmd_handle.store)
      self._latest_pipeline_run_op = ops.LatestPipelineRun.create(
          pipeline_name='pipeline-name')
      self._latest_pipeline_run_op.set_context(context)

      # Tests LatestPipelineRun with empty input.
      with self.assertRaises(exceptions.SkipSignal):
        self._latest_pipeline_run_op.apply()

  def testLatestPipelineRun_OneKey(self):
    with self.mlmd_handle as mlmd_handle:
      context = resolver_op.Context(store=mlmd_handle.store)
      self._latest_pipeline_run_op = ops.LatestPipelineRun.create(
          pipeline_name='pipeline-name')
      self._latest_pipeline_run_op.set_context(context)

      node_context = self.put_context('node', 'example-gen')
      end_node_context = self.put_context('node',
                                          'pipeline-name.pipeline-name_end')

      # Creates the first pipeline run and artifact.
      input_artifact_1 = self.put_artifact('Example')
      pipeline_run_ctx_1 = self.put_context('pipeline_run', 'run-001')
      self.put_execution(
          'ExampleGen',
          inputs={},
          outputs={'examples': [input_artifact_1]},
          contexts=[node_context, pipeline_run_ctx_1],
          output_event_type=metadata_store_pb2.Event.OUTPUT)
      self.put_execution(
          'EndNode',
          inputs={},
          outputs={'examples': [input_artifact_1]},
          contexts=[end_node_context, pipeline_run_ctx_1],
          output_event_type=metadata_store_pb2.Event.INTERNAL_OUTPUT)

      # Tests LatestPipelineRun with the first artifact.
      result = self._latest_pipeline_run_op.apply()
      expected_result = {'examples': [input_artifact_1]}
      self.assertAllEqual(result.keys(), expected_result.keys())
      for key in result.keys():
        result_ids = [a.mlmd_artifact.id for a in result[key]]
        expected_ids = [a.id for a in expected_result[key]]
        self.assertAllEqual(result_ids, expected_ids)

      # Creates the second pipeline run and artifact.
      input_artifact_2 = self.put_artifact('Example')
      pipeline_run_ctx_2 = self.put_context('pipeline_run', 'run-002')
      self.put_execution(
          'ExampleGen',
          inputs={},
          outputs={'examples': [input_artifact_2]},
          contexts=[node_context, pipeline_run_ctx_2, end_node_context],
          output_event_type=metadata_store_pb2.Event.OUTPUT)
      self.put_execution(
          'EndNode',
          inputs={},
          outputs={'examples': [input_artifact_2]},
          contexts=[end_node_context, pipeline_run_ctx_2],
          output_event_type=metadata_store_pb2.Event.INTERNAL_OUTPUT)

      # Tests LatestPipelineRun with the first and second artifacts.
      result = self._latest_pipeline_run_op.apply()
      expected_result = {'examples': [input_artifact_2]}
      self.assertAllEqual(result.keys(), expected_result.keys())
      for key in result.keys():
        result_ids = [a.mlmd_artifact.id for a in result[key]]
        expected_ids = [a.id for a in expected_result[key]]
        self.assertAllEqual(result_ids, expected_ids)

  def testLatestPipelineRun_TwoKeys(self):
    with self.mlmd_handle as mlmd_handle:
      context = resolver_op.Context(store=mlmd_handle.store)
      self._latest_pipeline_run_op = ops.LatestPipelineRun.create(
          pipeline_name='pipeline-name')
      self._latest_pipeline_run_op.set_context(context)

      example_gen_node_context = self.put_context('node', 'example-gen')
      statistics_gen_node_context = self.put_context('node', 'statistics-gen')
      end_node_context = self.put_context('node',
                                          'pipeline-name.pipeline-name_end')

      # First pipeline run generates two artifacts
      example_artifact_1 = self.put_artifact('Example')
      statistics_artifact_1 = self.put_artifact('Statistics')
      pipeline_run_ctx_1 = self.put_context('pipeline_run', 'run-001')
      self.put_execution(
          'ExampleGen',
          inputs={},
          outputs={'examples': [example_artifact_1]},
          contexts=[example_gen_node_context, pipeline_run_ctx_1],
          output_event_type=metadata_store_pb2.Event.OUTPUT)
      self.put_execution(
          'StatisticsGen',
          inputs={},
          outputs={'statistics': [statistics_artifact_1]},
          contexts=[statistics_gen_node_context, pipeline_run_ctx_1],
          output_event_type=metadata_store_pb2.Event.OUTPUT)
      self.put_execution(
          'EndNode',
          inputs={},
          outputs={
              'statistics': [statistics_artifact_1],
              'examples': [example_artifact_1]
          },
          contexts=[end_node_context, pipeline_run_ctx_1],
          output_event_type=metadata_store_pb2.Event.INTERNAL_OUTPUT)

      # Second pipeline run generates one artifact
      example_artifact_2 = self.put_artifact('Example')
      pipeline_run_ctx_2 = self.put_context('pipeline_run', 'run-002')
      self.put_execution(
          'ExampleGen',
          inputs={},
          outputs={'examples': [example_artifact_2]},
          contexts=[example_gen_node_context, pipeline_run_ctx_2],
          output_event_type=metadata_store_pb2.Event.OUTPUT)
      self.put_execution(
          'EndNode',
          inputs={},
          outputs={'examples': [example_artifact_2]},
          contexts=[end_node_context, pipeline_run_ctx_2],
          output_event_type=metadata_store_pb2.Event.INTERNAL_OUTPUT)

      # Only Examples are input
      result = self._latest_pipeline_run_op.apply()
      expected_result = {'examples': [example_artifact_2]}
      self.assertAllEqual(result.keys(), expected_result.keys())
      for key in result.keys():
        result_ids = [a.mlmd_artifact.id for a in result[key]]
        expected_ids = [a.id for a in expected_result[key]]
        self.assertAllEqual(result_ids, expected_ids)

      # Both Examples and Statistics are input
      result = self._latest_pipeline_run_op.apply()
      expected_result = {'examples': [example_artifact_2]}
      self.assertAllEqual(result.keys(), expected_result.keys())
      for key in result.keys():
        result_ids = [a.mlmd_artifact.id for a in result[key]]
        expected_ids = [a.id for a in expected_result[key]]
        self.assertAllEqual(result_ids, expected_ids)


if __name__ == '__main__':
  tf.test.main()
